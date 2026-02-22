"""Data processor for the Geoguessr API responses."""

import json
import logging
import math
from typing import Optional
from pathlib import Path

from src.models import GameResult, RoundResult

logger = logging.getLogger(__name__)

# Load countries once at module init
_COUNTRIES_FILE = Path(__file__).parent.parent / "data" / "countries.json"
try:
    with open(_COUNTRIES_FILE, "r", encoding="utf-8") as f:
        COUNTRIES = json.load(f)
except Exception as e:
    logger.error(f"Failed to load countries.json: {e}")
    COUNTRIES = {}


def get_country_name(code: str) -> str:
    """Resolve a 2-letter country code to a human-readable name."""
    if not code:
        return "Unknown"
    return COUNTRIES.get(code.lower(), code.upper())


def _is_duel(payload: dict) -> bool:
    """Check whether a feed payload represents a competitive duel."""
    return payload.get("gameMode") == "Duels" and "competitiveGameMode" in payload


def _get_guess(team: dict, round_number: int) -> dict:
    """Find a player's guess for a specific round number."""
    guesses = team["players"][0].get("guesses", [])
    return next((g for g in guesses if g.get("roundNumber") == round_number), {})


def _extract_rating(team: dict) -> Optional[float]:
    """Extract the post-game rating from a team's progress data.

    Returns None (which maps to NaN in pandas) when no rating is available,
    instead of 0.0, so missing ratings don't pollute averages.
    """
    player = team["players"][0]
    pc = player.get("progressChange")
    if pc is not None:
        cp = pc.get("competitiveProgress")
        if cp is not None:
            val = cp.get("ratingAfter")
            if val is not None:
                return float(val)
        rsp = pc.get("rankedSystemProgress")
        if rsp is not None:
            val = rsp.get("ratingAfter")
            if val is not None:
                return float(val)
    # Fallback to the base rating field (may be 0 for placement players)
    base = player.get("rating")
    if base is not None and base != 0:
        return float(base)
    return None  # Will become NaN in the DataFrame


def extract_duel_tokens(feed_entries: list[dict], limit: Optional[int] = None) -> list[str]:
    """Extract competitive duel game IDs from raw feed entries."""
    tokens = []
    for entry in feed_entries:
        payload_raw = entry.get("payload")
        if not payload_raw:
            continue

        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict):
            if _is_duel(payload):
                tokens.append(payload["gameId"])
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and "payload" in item and _is_duel(item["payload"]):
                    tokens.append(item["payload"]["gameId"])

        if limit and len(tokens) >= limit:
            return tokens[:limit]

    return tokens


def process_game(game_data: dict, my_player_id: str) -> Optional[GameResult]:
    """Process a raw game JSON into a GameResult object."""
    teams = game_data.get("teams", [])
    if len(teams) < 2:
        return None

    # Identify which team is the authenticated player
    my_team_idx = 0 if teams[0]["players"][0]["playerId"] == my_player_id else 1
    opp_team_idx = 1 - my_team_idx

    my_team = teams[my_team_idx]
    opp_team = teams[opp_team_idx]

    game_id = game_data.get("gameId")
    if not game_id:
        return None

    rounds_data = game_data.get("rounds", [])
    first_round_time = rounds_data[0].get("startTime") if rounds_data else None

    options = game_data.get("options", {})
    map_name = options.get("map", {}).get("name", "Unknown")
    game_mode = options.get("competitiveGameMode", "Unknown")

    move_opts = options.get("movementOptions", {})
    moving = not move_opts.get("forbidMoving", False)
    zooming = not move_opts.get("forbidZooming", False)
    rotating = not move_opts.get("forbidRotating", False)

    opp_player = opp_team["players"][0]
    opponent_id = opp_player.get("playerId", "Unknown")
    opponent_country = get_country_name(opp_player.get("countryCode", ""))

    my_rating = _extract_rating(my_team)
    opp_rating = _extract_rating(opp_team)

    # Game outcome from health
    my_health = my_team.get("health")
    opp_health = opp_team.get("health")

    game_won = None
    if my_health is not None and opp_health is not None:
        if my_health > 0 and opp_health <= 0:
            game_won = True
        elif opp_health > 0 and my_health <= 0:
            game_won = False

    game = GameResult(
        game_id=game_id,
        date=first_round_time,
        map_name=map_name,
        game_mode=game_mode,
        moving=moving, zooming=zooming, rotating=rotating,
        opponent_id=opponent_id,
        opponent_country=opponent_country,
        your_rating=my_rating,
        opponent_rating=opp_rating,
        game_won=game_won,
        your_health=my_health,
        opp_health=opp_health,
    )

    current_round_num = game_data.get("currentRoundNumber", len(rounds_data))

    for i in range(current_round_num):
        if i >= len(rounds_data):
            break

        rnd = rounds_data[i]
        round_num = rnd.get("roundNumber", i + 1)

        pano = rnd.get("panorama", {})
        country_code = pano.get("countryCode", "")
        country_name = get_country_name(country_code)
        lat = pano.get("lat", 0.0)
        lng = pano.get("lng", 0.0)
        dmg_mult = rnd.get("damageMultiplier")

        my_guess = _get_guess(my_team, round_num)
        opp_guess = _get_guess(opp_team, round_num)

        round_result = RoundResult(
            round_number=round_num,
            country=country_name,
            country_code=country_code,
            latitude=lat,
            longitude=lng,
            damage_multiplier=dmg_mult,
            your_lat=my_guess.get("lat", 0.0),
            your_lng=my_guess.get("lng", 0.0),
            your_distance_km=my_guess.get("distance", 0) / 1000.0,
            your_score=my_guess.get("score", 0),
            opp_lat=opp_guess.get("lat", 0.0),
            opp_lng=opp_guess.get("lng", 0.0),
            opp_distance_km=opp_guess.get("distance", 0) / 1000.0,
            opp_score=opp_guess.get("score", 0),
        )
        game.rounds.append(round_result)

    return game
