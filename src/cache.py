"""Cache and synchronization management for local game storage."""

import os
import logging
from typing import Callable, Optional, Tuple
import pandas as pd
from datetime import datetime

from src.api_client import GeoguessrClient
from src.processor import extract_duel_tokens, process_game
from src.models import PlayerInfo

logger = logging.getLogger(__name__)


def load_cache(cache_path: str) -> pd.DataFrame:
    """Load the games cache to a DataFrame."""
    if os.path.exists(cache_path):
        try:
            df = pd.read_json(cache_path, orient="records")
            if not df.empty and "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
            return df
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def save_cache(df: pd.DataFrame, cache_path: str):
    """Save the DataFrame to local JSON cache."""
    if df.empty:
        return
    try:
        df.to_json(cache_path, orient="records", date_format="iso")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def sync_data(
    client: GeoguessrClient,
    cache_path: str,
    progress_cb: Optional[Callable[[float], None]] = None
) -> Tuple[pd.DataFrame, int, PlayerInfo]:
    """Sync data from Geoguessr limits updates to missing remote tokens."""
    
    # Authenticate and get player info
    player_data_raw = client.get_player_info()
    player_info = PlayerInfo(id=player_data_raw["id"], nick=player_data_raw["nick"])
    
    # Load Cache
    df_existing = load_cache(cache_path)
    existing_ids = set()
    if not df_existing.empty:
        existing_ids = set(df_existing["Game Id"].unique())
        
    # Fetch Tokens
    # Usually we would traverse pages until a known game ID is found.
    # For simplicity, we limit token loading pages
    remote_tokens = []
    pagination_token = None
    STOP_DATE = datetime(2023, 1, 1).date()
    
    while True:
        try:
            feed_page = client.get_feed_page(pagination_token)
            entries = feed_page.get("entries", [])
            if not entries:
                break
                
            remote_tokens.extend(extract_duel_tokens(entries))
            
            # Check date of first entry on this page to potentially stop pagination
            # But the feed can be slightly out of order, so it's a heuristic
            first_entry_time = entries[0].get("time")
            if first_entry_time:
                try:
                    entry_date = datetime.fromisoformat(first_entry_time.replace("Z", "+00:00")).date()
                    if entry_date < STOP_DATE:
                        break
                except ValueError:
                    pass
            
            pagination_token = feed_page.get("paginationToken")
            if not pagination_token:
                break
        except Exception as e:
            logger.warning(f"Error fetching tokens on pagination: {e}")
            break
            
    # Filter only new tokens
    tokens_to_fetch = [t for t in remote_tokens if t not in existing_ids]
    
    if not tokens_to_fetch:
        return df_existing, 0, player_info
        
    new_rows = []
    total = len(tokens_to_fetch)
    for i, token in enumerate(tokens_to_fetch):
        if progress_cb:
            progress_cb(i / total)
            
        try:
            game_data = client.get_game_details(token)
            game_result = process_game(game_data, player_info.id)
            if game_result:
                new_rows.extend(game_result.to_flat_rows())
        except Exception as e:
            logger.warning(f"Error processing game {token}: {e}")
            
    if progress_cb:
        progress_cb(1.0)
        
    df_new = pd.DataFrame(new_rows)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True) if not df_existing.empty else df_new
    df_combined.drop_duplicates(subset=["Game Id", "Round Number"], inplace=True)
    save_cache(df_combined, cache_path)
    
    return df_combined, len(tokens_to_fetch), player_info
