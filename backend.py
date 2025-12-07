import requests
import pandas as pd
import numpy as np
import json
import datetime
import os
from datetime import timedelta

CACHE_FILE = "games_cache.json"

class GeoguessrBackend:
    def __init__(self, ncfa_token):
        self.session = requests.Session()
        self.session.cookies.set("_ncfa", ncfa_token, domain="www.geoguessr.com")
        self.base_url_v4 = "https://www.geoguessr.com/api/v4"
        self.base_url_v3 = "https://game-server.geoguessr.com/api/duels"

    def get_player_data(self):
        try:
            response = self.session.get(f"{self.base_url_v4}/feed/private")
            if response.status_code != 200:
                return {}
            data = response.json()
            if not data.get('entries'):
                return {}
            player_data = data['entries'][0]['user']
            return {'id': player_data['id'], 'nick': player_data['nick']}
        except Exception as e:
            print(f"Error fetching player data: {e}")
            return {}

    def get_all_duel_tokens(self, limit=None):
        """
        Fetches the list of all competitive duel tokens (game IDs) from the feed.
        This iterates through the pagination until it finds all games or hits a date limit.
        """
        game_tokens = []
        pagination_token = None
        
        # Robustness: We stop if we hit games older than a certain logical start date 
        # or if we just want to sync recent ones. 
        # For a full sync, we might need to go back far. 
        # But existing logic had a hardcoded date "2024-07-01", I will keep that as a reasonable default/guardrail
        # or perhaps make it configurable. I'll use a safe past date.
        STOP_DATE = datetime.date(2023, 1, 1) 

        while True:
            params = {'paginationToken': pagination_token} if pagination_token else {}
            try:
                response = self.session.get(f"{self.base_url_v4}/feed/private", params=params)
                if response.status_code != 200:
                    break
                
                data = response.json()
                if 'entries' not in data:
                    break
                
                entries = data['entries']
                for entry in entries:
                    # Date Check
                    game_time_str = entry.get('time')
                    if game_time_str:
                        # Handle varied ISO formats if necessary, but fromisoformat usually works
                        try:
                            game_date = datetime.datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).date()
                            if game_date < STOP_DATE:
                                return game_tokens 
                        except ValueError:
                            pass

                    payload_raw = entry.get('payload')
                    if not payload_raw:
                        continue
                        
                    try:
                        payload_json = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        continue

                    # Helper to check if payload is a duel
                    def is_duel(p):
                        return p.get('gameMode') == 'Duels' and 'competitiveGameMode' in p

                    if isinstance(payload_json, dict):
                        if is_duel(payload_json):
                            game_tokens.append(payload_json['gameId'])
                    elif isinstance(payload_json, list):
                        for item in payload_json:
                            if isinstance(item, dict) and 'payload' in item:
                                if is_duel(item['payload']):
                                    game_tokens.append(item['payload']['gameId'])
                
                pagination_token = data.get('paginationToken')
                if not pagination_token:
                    break
                
                if limit and len(game_tokens) >= limit:
                    return game_tokens[:limit]
                    
            except Exception as e:
                print(f"Error in token fetch loop: {e}")
                break
                
        return game_tokens

    def fetch_game_details(self, game_ids, my_player_id, progress_callback=None):
        """
        Fetches detailed stats for a list of game IDs.
        """
        new_games_data = []
        total = len(game_ids)
        
        for i, token in enumerate(game_ids):
            if progress_callback:
                progress_callback(i / total)
                
            try:
                response = self.session.get(f"{self.base_url_v3}/{token}")
                if response.status_code == 200:
                    game = response.json()
                    processed_game = self._process_single_game(game, my_player_id)
                    if processed_game:
                        new_games_data.extend(processed_game)
            except Exception as e:
                print(f"Failed to fetch game {token}: {e}")
                continue
                
        return new_games_data

    def _process_single_game(self, game, my_player_id):
        """Internal helper to process one raw game JSON into rows."""
        rows = []
        
        # Identify teams
        teams = game.get('teams', [])
        if len(teams) < 2: 
            return []
            
        # Find "Me"
        me_idx = 0
        other_idx = 1
        
        p1_id = teams[0]['players'][0]['playerId']
        if p1_id != my_player_id:
            me_idx = 1
            other_idx = 0
            
        me_team = teams[me_idx]
        other_team = teams[other_idx]
        
        # Meta info
        game_id = game['gameId']
        # Use first round start time as game date, fallback to now if missing
        first_round_time = game.get('rounds', [{}])[0].get('startTime')
        map_name = game.get('options', {}).get('map', {}).get('name', 'Unknown')
        game_mode = game.get('options', {}).get('competitiveGameMode', 'Unknown')
        
        # Movement options
        opts = game.get('options', {}).get('movementOptions', {})
        is_moving = not opts.get('forbidMoving', False)
        is_zooming = not opts.get('forbidZooming', False)
        is_rotating = not opts.get('forbidRotating', False)
        
        opponent_id = other_team['players'][0]['playerId']
        opponent_country = self._get_country_name(other_team['players'][0].get('countryCode', ''))
        
        # Rating delta handling
        # It seems complex in original code, simplifying slightly but keeping logic
        def get_rating(team_data):
            # Try progressively specific fields
            pc = team_data['players'][0].get('progressChange')
            if pc:
                if pc.get('competitiveProgress'):
                    return pc['competitiveProgress'].get('ratingAfter')
                elif pc.get('rankedSystemProgress'):
                    return pc['rankedSystemProgress'].get('ratingAfter')
            # Fallback
            return team_data['players'][0].get('rating')

        my_rating = get_rating(me_team)
        opp_rating = get_rating(other_team)
        
        # Rounds
        rounds = game.get('rounds', [])
        current_round_num = game.get('currentRoundNumber', len(rounds))
        
        for i in range(current_round_num):
            if i >= len(rounds): break
            
            rnd = rounds[i]
            round_num = rnd['roundNumber']
            
            # Panorama info
            pano = rnd.get('panorama', {})
            country_code = pano.get('countryCode', '')
            country_name = self._get_country_name(country_code)
            lat = pano.get('lat')
            lng = pano.get('lng')
            
            # Guesses
            # Helper to find guess for specific round number
            def find_guess(team, r_num):
                guesses = team['players'][0].get('guesses', [])
                for g in guesses:
                    if g['roundNumber'] == r_num:
                        return g
                return None

            my_guess = find_guess(me_team, round_num)
            other_guess = find_guess(other_team, round_num)
            
            # Prepare row
            row = {
                'Game Id': game_id,
                'Date': first_round_time,
                'Round Number': round_num,
                'Country': country_name,
                'Latitude': lat,
                'Longitude': lng,
                'Damage Multiplier': rnd.get('damageMultiplier'),
                'Map Name': map_name,
                'Game Mode': game_mode,
                'Moving': is_moving,
                'Zooming': is_zooming,
                'Rotating': is_rotating,
                'Opponent Id': opponent_id,
                'Opponent Country': opponent_country,
                'Your Rating': my_rating,
                'Opponent Rating': opp_rating,
            }
            
            # My stats
            if my_guess:
                row['Your Latitude'] = my_guess.get('lat')
                row['Your Longitude'] = my_guess.get('lng')
                row['Your Distance'] = my_guess.get('distance', 0) / 1000.0 # convert to km
                row['Your Score'] = my_guess.get('score')
            else:
                row['Your Latitude'] = 0
                row['Your Longitude'] = 0
                row['Your Distance'] = 0
                row['Your Score'] = 0
                
            # Opponent stats
            if other_guess:
                row['Opponent Latitude'] = other_guess.get('lat')
                row['Opponent Longitude'] = other_guess.get('lng')
                row['Opponent Distance'] = other_guess.get('distance', 0) / 1000.0
                row['Opponent Score'] = other_guess.get('score')
            else:
                row['Opponent Latitude'] = 0
                row['Opponent Longitude'] = 0
                row['Opponent Distance'] = 0
                row['Opponent Score'] = 0
                
            # Derived
            row['Score Difference'] = row['Your Score'] - row['Opponent Score']
            row['Win Percentage'] = 100 if row['Your Score'] > row['Opponent Score'] else 0
            
            rows.append(row)
            
        return rows

    def _get_country_name(self, code):
        if not code: return "Unknown"
        # Minimal map for now, ideally this is in a separate file or the big dict from before
        # I will include the big dict from the original file for completeness
        code = code.lower()
        # This is a truncated list for brevity in this prompt, but in real file I'd paste the whole thing.
        # TO ensure functionality I will paste the full dictionary logic here.
        
        # ... (I will paste the full dict from main.py in the actual file write, abbreviated here for thought process)
        # For now I'll just use a small dict and return code if missing, or maybe I should copy the big one.
        # I'll copy the big one.
        return self.country_name_dict.get(code, code)

    country_name_dict = {
         'ad': 'Andorra', 'ae': 'United Arab Emirates', 'af': 'Afghanistan', 'ag': 'Antigua and Barbuda',
         'ai': 'Anguilla', 'al': 'Albania', 'am': 'Armenia', 'ao': 'Angola', 'aq': 'Antarctica',
         'ar': 'Argentina', 'as': 'American Samoa', 'at': 'Austria', 'au': 'Australia', 'aw': 'Aruba',
         'ax': 'Åland Islands', 'az': 'Azerbaijan', 'ba': 'Bosnia and Herzegovina', 'bb': 'Barbados',
         'bd': 'Bangladesh', 'be': 'Belgium', 'bf': 'Burkina Faso', 'bg': 'Bulgaria', 'bh': 'Bahrain',
         'bi': 'Burundi', 'bj': 'Benin', 'bl': 'Saint Barthélemy', 'bm': 'Bermuda', 'bn': 'Brunei Darussalam',
         'bo': 'Bolivia', 'bq': 'Bonaire, Sint Eustatius and Saba', 'br': 'Brazil', 'bs': 'Bahamas',
         'bt': 'Bhutan', 'bv': 'Bouvet Island', 'bw': 'Botswana', 'by': 'Belarus', 'bz': 'Belize',
         'ca': 'Canada', 'cc': 'Cocos (Keeling) Islands', 'cd': 'Congo (Democratic Republic of the)',
         'cf': 'Central African Republic', 'cg': 'Congo', 'ch': 'Switzerland', 'ci': 'Côte d\'Ivoire',
         'ck': 'Cook Islands', 'cl': 'Chile', 'cm': 'Cameroon', 'cn': 'China', 'co': 'Colombia',
         'cr': 'Costa Rica', 'cu': 'Cuba', 'cv': 'Cabo Verde', 'cw': 'Curaçao', 'cx': 'Christmas Island',
         'cy': 'Cyprus', 'cz': 'Czechia', 'de': 'Germany', 'dj': 'Djibouti', 'dk': 'Denmark',
         'dm': 'Dominica', 'do': 'Dominican Republic', 'dz': 'Algeria', 'ec': 'Ecuador', 'ee': 'Estonia',
         'eg': 'Egypt', 'eh': 'Western Sahara', 'er': 'Eritrea', 'es': 'Spain', 'et': 'Ethiopia',
         'fi': 'Finland', 'fj': 'Fiji', 'fk': 'Falkland Islands (Malvinas)',
         'fm': 'Micronesia (Federated States of)', 'fo': 'Faroe Islands', 'fr': 'France', 'ga': 'Gabon',
         'gb': 'United Kingdom', 'gd': 'Grenada', 'ge': 'Georgia', 'gf': 'French Guiana', 'gg': 'Guernsey',
         'gh': 'Ghana', 'gi': 'Gibraltar', 'gl': 'Greenland', 'gm': 'Gambia', 'gn': 'Guinea',
         'gp': 'Guadeloupe', 'gq': 'Equatorial Guinea', 'gr': 'Greece',
         'gs': 'South Georgia and the South Sandwich Islands', 'gt': 'Guatemala', 'gu': 'Guam',
         'gw': 'Guinea-Bissau', 'gy': 'Guyana', 'hk': 'Hong Kong',
         'hm': 'Heard Island and McDonald Islands', 'hn': 'Honduras', 'hr': 'Croatia', 'ht': 'Haiti',
         'hu': 'Hungary', 'id': 'Indonesia', 'ie': 'Ireland', 'il': 'Israel', 'im': 'Isle of Man',
         'in': 'India', 'io': 'British Indian Ocean Territory', 'iq': 'Iraq', 'ir': 'Iran', 'is': 'Iceland',
         'it': 'Italy', 'je': 'Jersey', 'jm': 'Jamaica', 'jo': 'Jordan', 'jp': 'Japan', 'ke': 'Kenya',
         'kg': 'Kyrgyzstan', 'kh': 'Cambodia', 'ki': 'Kiribati', 'km': 'Comoros',
         'kn': 'Saint Kitts and Nevis', 'kp': 'North Korea', 'kr': 'South Korea', 'kw': 'Kuwait',
         'ky': 'Cayman Islands', 'kz': 'Kazakhstan', 'la': 'Laos', 'lb': 'Lebanon', 'lc': 'Saint Lucia',
         'li': 'Liechtenstein', 'lk': 'Sri Lanka', 'lr': 'Liberia', 'ls': 'Lesotho', 'lt': 'Lithuania',
         'lu': 'Luxembourg', 'lv': 'Latvia', 'ly': 'Libya', 'ma': 'Morocco', 'mc': 'Monaco',
         'md': 'Moldova', 'me': 'Montenegro', 'mf': 'Saint Martin', 'mg': 'Madagascar',
         'mh': 'Marshall Islands', 'mk': 'North Macedonia', 'ml': 'Mali', 'mm': 'Myanmar', 'mn': 'Mongolia',
         'mo': 'Macao', 'mp': 'Northern Mariana Islands', 'mq': 'Martinique', 'mr': 'Mauritania',
         'ms': 'Montserrat', 'mt': 'Malta', 'mu': 'Mauritius', 'mv': 'Maldives', 'mw': 'Malawi',
         'mx': 'Mexico', 'my': 'Malaysia', 'mz': 'Mozambique', 'na': 'Namibia', 'nc': 'New Caledonia',
         'ne': 'Niger', 'nf': 'Norfolk Island', 'ng': 'Nigeria', 'ni': 'Nicaragua', 'nl': 'Netherlands',
         'no': 'Norway', 'np': 'Nepal', 'nr': 'Nauru', 'nu': 'Niue', 'nz': 'New Zealand', 'om': 'Oman',
         'pa': 'Panama', 'pe': 'Peru', 'pf': 'French Polynesia', 'pg': 'Papua New Guinea',
         'ph': 'Philippines', 'pk': 'Pakistan', 'pl': 'Poland', 'pm': 'Saint Pierre and Miquelon',
         'pn': 'Pitcairn', 'pr': 'Puerto Rico', 'ps': 'Palestine', 'pt': 'Portugal', 'pw': 'Palau',
         'py': 'Paraguay', 'qa': 'Qatar', 're': 'Réunion', 'ro': 'Romania', 'rs': 'Serbia', 'ru': 'Russia',
         'rw': 'Rwanda', 'sa': 'Saudi Arabia', 'sb': 'Solomon Islands', 'sc': 'Seychelles', 'sd': 'Sudan',
         'se': 'Sweden', 'sg': 'Singapore', 'sh': 'Saint Helena', 'si': 'Slovenia',
         'sj': 'Svalbard and Jan Mayen', 'sk': 'Slovakia', 'sl': 'Sierra Leone', 'sm': 'San Marino',
         'sn': 'Senegal', 'so': 'Somalia', 'sr': 'Suriname', 'ss': 'South Sudan',
         'st': 'Sao Tome and Principe', 'sv': 'El Salvador', 'sx': 'Sint Maarten', 'sy': 'Syria',
         'sz': 'Eswatini', 'tc': 'Turks and Caicos Islands', 'td': 'Chad',
         'tf': 'French Southern Territories', 'tg': 'Togo', 'th': 'Thailand', 'tj': 'Tajikistan',
         'tk': 'Tokelau', 'tl': 'Timor-Leste', 'tm': 'Turkmenistan', 'tn': 'Tunisia', 'to': 'Tonga',
         'tr': 'Turkey', 'tt': 'Trinidad and Tobago', 'tv': 'Tuvalu', 'tw': 'Taiwan', 'tz': 'Tanzania',
         'ua': 'Ukraine', 'ug': 'Uganda', 'um': 'United States Minor Outlying Islands', 'us': 'United States',
         'uy': 'Uruguay', 'uz': 'Uzbekistan', 'va': 'Vatican City', 'vc': 'Saint Vincent and the Grenadines',
         've': 'Venezuela', 'vg': 'British Virgin Islands', 'vi': 'U.S. Virgin Islands', 'vn': 'Vietnam',
         'vu': 'Vanuatu', 'wf': 'Wallis and Futuna', 'ws': 'Samoa', 'xk': 'Kosovo', 'ye': 'Yemen',
         'yt': 'Mayotte', 'za': 'South Africa', 'zm': 'Zambia', 'zw': 'Zimbabwe',
    }

class DataManager:
    @staticmethod
    def load_cache():
        if os.path.exists(CACHE_FILE):
            try:
                df = pd.read_json(CACHE_FILE, orient='records')
                # Ensure date parsing
                if not df.empty and 'Date' in df.columns:
                     # Standardize date format to datetime objects
                    df['Date'] = pd.to_datetime(df['Date'])
                return df
            except Exception as e:
                print(f"Error loading cache: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    @staticmethod
    def save_cache(df):
        try:
            # Convert datetime to string for JSON serialization compatibility if needed, 
            # but read_json/to_json usually handles it. 
            df.to_json(CACHE_FILE, orient='records', date_format='iso')
        except Exception as e:
            print(f"Error saving cache: {e}")

    @staticmethod
    def sync_data(ncfa_token, progress_callback=None):
        """
        Syncs local cache with remote API.
        Returns: Tuple of (Updated DataFrame, new_games_count)
        """
        backend = GeoguessrBackend(ncfa_token)
        player_data = backend.get_player_data()
        if not player_data:
            raise ValueError("Invalid Token or Unable to fetch player data")

        # 1. Load Local
        existing_df = DataManager.load_cache()
        existing_ids = set(existing_df['Game Id'].unique()) if not existing_df.empty else set()

        # 2. Fetch Remote Tokens (All or recent)
        # To be safe, we fetch recent ones first. 
        # But the user wants a cache. 
        # Strategy: Fetch 'All' tokens from feed. 
        # Ideally we stop fetching tokens once we see one we already have, 
        # but the feed isn't perfectly strictly ordered? It usually is. 
        # For simplicity, let's fetch all tokens (it's just IDs, fast) 
        # or fetch until we hit a known ID.
        
        # Let's try fetching all tokens (it was fast enough in original code presumably)
        remote_tokens = backend.get_all_duel_tokens()
        
        # 3. Diff
        tokens_to_fetch = [t for t in remote_tokens if t not in existing_ids]
        
        # 4. Fetch Details if needed
        if tokens_to_fetch:
            new_data = backend.fetch_game_details(
                tokens_to_fetch, 
                player_data['id'], 
                progress_callback=progress_callback
            )
            
            if new_data:
                new_df = pd.DataFrame(new_data)
                # 5. Merge and Save
                updated_df = pd.concat([existing_df, new_df], ignore_index=True) if not existing_df.empty else new_df
                # Drop duplicates just in case
                updated_df.drop_duplicates(subset=['Game Id', 'Round Number'], inplace=True)
                DataManager.save_cache(updated_df)
                return updated_df, len(tokens_to_fetch), player_data
        
        return existing_df, 0, player_data
