"""Data models for the Duels Analyzer."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class PlayerInfo:
    """Authenticated player information."""
    id: str
    nick: str


@dataclass
class RoundResult:
    """A single round within a duel game."""
    round_number: int
    country: str
    country_code: str
    latitude: float
    longitude: float
    damage_multiplier: Optional[float] = None

    # Player's guess
    your_lat: float = 0.0
    your_lng: float = 0.0
    your_distance_km: float = 0.0
    your_score: int = 0

    # Opponent's guess
    opp_lat: float = 0.0
    opp_lng: float = 0.0
    opp_distance_km: float = 0.0
    opp_score: int = 0

    @property
    def score_difference(self) -> int:
        return self.your_score - self.opp_score

    @property
    def round_won(self) -> bool:
        return self.your_score > self.opp_score


@dataclass
class GameResult:
    """A complete duel game with all its rounds."""
    game_id: str
    date: Optional[str] = None
    map_name: str = "Unknown"
    game_mode: str = "Unknown"

    # Movement options
    moving: bool = True
    zooming: bool = True
    rotating: bool = True

    # Players
    opponent_id: str = ""
    opponent_country: str = "Unknown"
    your_rating: Optional[float] = None
    opponent_rating: Optional[float] = None

    # Game outcome
    game_won: Optional[bool] = None  # None if game incomplete
    your_health: Optional[float] = None
    opp_health: Optional[float] = None

    rounds: list[RoundResult] = field(default_factory=list)

    def to_flat_rows(self) -> list[dict]:
        """Convert to flat round-level dicts for DataFrame creation."""
        rows = []
        for rnd in self.rounds:
            rows.append({
                "Game Id": self.game_id,
                "Date": self.date,
                "Round Number": rnd.round_number,
                "Country": rnd.country,
                "Country Code": rnd.country_code,
                "Latitude": rnd.latitude,
                "Longitude": rnd.longitude,
                "Damage Multiplier": rnd.damage_multiplier,
                "Map Name": self.map_name,
                "Game Mode": self.game_mode,
                "Moving": self.moving,
                "Zooming": self.zooming,
                "Rotating": self.rotating,
                "Opponent Id": self.opponent_id,
                "Opponent Country": self.opponent_country,
                "Your Rating": self.your_rating,
                "Opponent Rating": self.opponent_rating,
                "Your Latitude": rnd.your_lat,
                "Your Longitude": rnd.your_lng,
                "Your Distance": rnd.your_distance_km,
                "Your Score": rnd.your_score,
                "Opponent Latitude": rnd.opp_lat,
                "Opponent Longitude": rnd.opp_lng,
                "Opponent Distance": rnd.opp_distance_km,
                "Opponent Score": rnd.opp_score,
                "Score Difference": rnd.score_difference,
                "Round Won": rnd.round_won,
                "Game Won": self.game_won,
                "Your Health": self.your_health,
                "Opponent Health": self.opp_health,
            })
        return rows
