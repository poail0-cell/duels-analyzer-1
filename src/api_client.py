"""HTTP client for the Geoguessr API."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class GeoguessrAPIError(Exception):
    """Raised when an API request fails."""
    pass


class GeoguessrClient:
    """Handles all HTTP communication with the Geoguessr API."""

    BASE_URL_V4 = "https://www.geoguessr.com/api/v4"
    BASE_URL_DUELS = "https://game-server.geoguessr.com/api/duels"

    def __init__(self, ncfa_token: str):
        self.session = requests.Session()
        self.session.cookies.set("_ncfa", ncfa_token, domain="www.geoguessr.com")

    def get_player_info(self) -> dict:
        """Fetch the authenticated player's basic info.

        Returns:
            dict with 'id' and 'nick' keys.

        Raises:
            GeoguessrAPIError: If the request fails or data is missing.
        """
        try:
            resp = self.session.get(f"{self.BASE_URL_V4}/feed/private")
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("entries")
            if not entries:
                raise GeoguessrAPIError("No entries found in feed — token may be invalid.")
            user = entries[0]["user"]
            return {"id": user["id"], "nick": user["nick"]}
        except requests.RequestException as e:
            raise GeoguessrAPIError(f"Failed to fetch player info: {e}") from e

    def get_feed_page(self, pagination_token: Optional[str] = None) -> dict:
        """Fetch a single page of the private feed.

        Args:
            pagination_token: Token for the next page, or None for the first page.

        Returns:
            Raw JSON dict with 'entries' and 'paginationToken' keys.
        """
        params = {}
        if pagination_token:
            params["paginationToken"] = pagination_token

        try:
            resp = self.session.get(f"{self.BASE_URL_V4}/feed/private", params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise GeoguessrAPIError(f"Failed to fetch feed page: {e}") from e

    def get_game_details(self, game_id: str) -> dict:
        """Fetch full details for a single duel game.

        Args:
            game_id: The game token/ID.

        Returns:
            Raw JSON dict with full game data.
        """
        try:
            resp = self.session.get(f"{self.BASE_URL_DUELS}/{game_id}")
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise GeoguessrAPIError(f"Failed to fetch game {game_id}: {e}") from e
