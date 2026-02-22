"""Pandas DataFrame aggregation helpers for all analytics views."""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Core aggregations
# ---------------------------------------------------------------------------

def stats_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate round-level stats grouped by panorama country."""
    by_country = df.groupby("Country").agg({
        "Your Score": "mean",
        "Opponent Score": "mean",
        "Score Difference": "mean",
        "Round Won": "mean",
        "Country": "count",
        "Your Distance": "mean",
    })
    by_country.rename(columns={
        "Country": "Rounds", "Your Distance": "Distance", "Round Won": "Win Rate"
    }, inplace=True)
    by_country["Win Rate"] = by_country["Win Rate"] * 100
    by_country = by_country.round(2).reset_index()
    return by_country.sort_values("Rounds", ascending=False)


def stats_by_round(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate performance metrics per round number (1-5)."""
    by_round = df.groupby("Round Number").agg({
        "Your Score": "mean",
        "Opponent Score": "mean",
        "Score Difference": "mean",
        "Round Won": "mean",
        "Round Number": "count",
        "Your Distance": "mean",
    })
    by_round.rename(columns={
        "Round Number": "Count", "Your Distance": "Distance", "Round Won": "Win Rate"
    }, inplace=True)
    by_round["Win Rate"] = by_round["Win Rate"] * 100
    return by_round.round(2).reset_index()


def stats_by_opponent_country(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate performance grouped by opponent nationality."""
    by_opp = df.groupby("Opponent Country").agg({
        "Your Score": "mean",
        "Opponent Score": "mean",
        "Score Difference": "mean",
        "Round Won": "mean",
        "Country": "count",
        "Your Distance": "mean",
    })
    by_opp.rename(columns={
        "Country": "Rounds", "Your Distance": "Distance", "Round Won": "Win Rate"
    }, inplace=True)
    by_opp["Win Rate"] = by_opp["Win Rate"] * 100
    return by_opp.round(2).reset_index()


# ---------------------------------------------------------------------------
# Time series helpers
# ---------------------------------------------------------------------------

def rating_history(df: pd.DataFrame) -> pd.DataFrame:
    """One row per game with date and rating for timeline charts."""
    games = df.sort_values("Date").groupby("Game Id").first().reset_index()
    return games[["Date", "Your Rating", "Opponent Rating", "Game Won"]].dropna(subset=["Your Rating"])


def rating_change_per_game(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the delta in rating between consecutive games."""
    games = df.sort_values("Date").groupby("Game Id").first().reset_index()
    games = games.dropna(subset=["Your Rating"])
    games["Rating Change"] = games["Your Rating"].diff()
    return games[["Date", "Game Id", "Your Rating", "Rating Change", "Game Won"]].iloc[1:]


def binned_metrics(df: pd.DataFrame, metric_col: str, period: str = "M") -> pd.DataFrame:
    """Group a metric by time period (W/M/Y) and return period averages."""
    tmp = df.copy()
    tmp["Date"] = pd.to_datetime(tmp["Date"])
    tmp["Period"] = tmp["Date"].dt.to_period(period).apply(lambda r: r.start_time)
    return tmp.groupby("Period")[metric_col].mean().reset_index()


def games_played_over_time(df: pd.DataFrame, period: str = "W") -> pd.DataFrame:
    """Count unique games per time period."""
    tmp = df.copy()
    tmp["Date"] = pd.to_datetime(tmp["Date"])
    tmp["Period"] = tmp["Date"].dt.to_period(period).apply(lambda r: r.start_time)
    return tmp.groupby("Period")["Game Id"].nunique().reset_index().rename(columns={"Game Id": "Games Played"})


# ---------------------------------------------------------------------------
# Win rate and streaks
# ---------------------------------------------------------------------------

def game_win_rate(df: pd.DataFrame) -> float:
    """Calculate the overall game win rate (%)."""
    games = df.groupby("Game Id")["Game Won"].first().dropna()
    if len(games) == 0:
        return 0.0
    return (games.sum() / len(games)) * 100


def streaks(df: pd.DataFrame) -> dict:
    """Compute current and longest win/loss streaks."""
    games = df.sort_values("Date").groupby("Game Id")["Game Won"].first().dropna()
    if len(games) == 0:
        return {"current_streak": 0, "current_type": "N/A",
                "longest_win": 0, "longest_loss": 0}

    results = games.values.astype(bool)

    # Current streak
    current_val = results[-1]
    current_count = 0
    for v in reversed(results):
        if v == current_val:
            current_count += 1
        else:
            break

    # Longest streaks
    longest_win = longest_loss = 0
    run = 0
    prev = None
    for v in results:
        if v == prev:
            run += 1
        else:
            run = 1
            prev = v
        if v:
            longest_win = max(longest_win, run)
        else:
            longest_loss = max(longest_loss, run)

    return {
        "current_streak": current_count,
        "current_type": "Win" if current_val else "Loss",
        "longest_win": longest_win,
        "longest_loss": longest_loss,
    }


# ---------------------------------------------------------------------------
# Head-to-head
# ---------------------------------------------------------------------------

def head_to_head(df: pd.DataFrame) -> pd.DataFrame:
    """Find opponents faced more than once and aggregate results."""
    games = df.groupby("Game Id").agg({
        "Opponent Id": "first",
        "Opponent Country": "first",
        "Game Won": "first",
        "Your Score": "sum",
        "Opponent Score": "sum",
    }).reset_index()

    repeat = games.groupby("Opponent Id").agg({
        "Game Id": "count",
        "Opponent Country": "first",
        "Game Won": lambda x: x.dropna().sum(),
        "Your Score": "mean",
        "Opponent Score": "mean",
    }).rename(columns={"Game Id": "Games", "Game Won": "Wins"})

    repeat = repeat[repeat["Games"] > 1].sort_values("Games", ascending=False)
    repeat["Losses"] = repeat["Games"] - repeat["Wins"]
    return repeat.reset_index()


# ---------------------------------------------------------------------------
# Top-level overview helper
# ---------------------------------------------------------------------------

def get_stats_overview(df: pd.DataFrame) -> dict:
    """Compute headline metrics for the metric cards."""
    if df.empty:
        return {
            "total_games": 0, "current_rating": 0,
            "round_win_rate": 0, "avg_score": 0,
            "game_win_rate": 0, "avg_distance": 0,
        }

    games_df = df.sort_values("Date").groupby("Game Id").first()
    total_games = len(games_df)

    # Current rating = latest non-null rating
    rating_series = games_df["Your Rating"].dropna()
    current_rating = rating_series.iloc[-1] if not rating_series.empty else 0

    round_win_rate = df["Round Won"].mean() * 100
    g_win_rate = game_win_rate(df)
    avg_score = df["Your Score"].mean()
    avg_distance = df["Your Distance"].mean()

    return {
        "total_games": total_games,
        "current_rating": current_rating,
        "round_win_rate": round_win_rate,
        "game_win_rate": g_win_rate,
        "avg_score": avg_score,
        "avg_distance": avg_distance,
    }
