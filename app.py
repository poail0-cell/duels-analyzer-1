"""Main entry point for Duels Analyzer Streamlit Application."""

import streamlit as st
from datetime import timedelta
import pandas as pd

from src.api_client import GeoguessrClient
from src.cache import load_cache, sync_data
from src.analytics import get_stats_overview

from ui.styles import inject_styles
from ui.components import render_header, render_metric_cards, render_filters
from ui import tab_overview, tab_geography, tab_analysis, tab_data

CACHE_FILE = "games_cache.json"

TIMEZONE_OPTIONS = {
    "UTC": (0, 0),
    "IST (UTC+5:30)": (5, 30),
    "CET (UTC+1)": (1, 0),
    "EST (UTC-5)": (-5, 0),
    "PST (UTC-8)": (-8, 0),
    "JST (UTC+9)": (9, 0),
    "AEST (UTC+10)": (10, 0),
}

st.set_page_config(
    page_title="Geo-Duels Analyzer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()


def apply_timezone(df: pd.DataFrame, hours: int, minutes: int) -> pd.DataFrame:
    """Shift UTC dates by a fixed offset."""
    if df.empty:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Date"] = df["Date"] + timedelta(hours=hours, minutes=minutes)
    return df


def main():
    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("⚙️ Configuration")
        token_input = st.text_input(
            "Geoguessr _ncfa Cookie", type="password",
            help="Required for fetching data from the API",
        )

        if token_input:
            st.session_state["ncfa_token"] = token_input

        sync_btn = st.button("🔄 Sync New Games", type="primary", use_container_width=True)

        st.divider()

        tz_label = st.selectbox("Timezone", list(TIMEZONE_OPTIONS.keys()), index=0)
        tz_hours, tz_minutes = TIMEZONE_OPTIONS[tz_label]

        st.divider()
        st.caption("Data is cached locally in `games_cache.json`.")

    # ── Load cache ────────────────────────────────────────────────────────
    df = load_cache(CACHE_FILE)
    player_nick = st.session_state.get("player_nick", "")

    # ── Sync ──────────────────────────────────────────────────────────────
    if sync_btn and st.session_state.get("ncfa_token"):
        try:
            with st.status("Syncing with Geoguessr Server…", expanded=True) as status:
                st.write("Authenticating and checking for new games…")

                client = GeoguessrClient(st.session_state["ncfa_token"])
                progress_bar = st.progress(0.0)

                df_updated, new_count, p_info = sync_data(
                    client=client,
                    cache_path=CACHE_FILE,
                    progress_cb=progress_bar.progress,
                )

                df = df_updated
                st.session_state["player_nick"] = p_info.nick
                player_nick = p_info.nick

                status.update(
                    label=f"Sync Complete! (+{new_count} new games)",
                    state="complete", expanded=False,
                )
                st.rerun()

        except Exception as e:
            st.error(f"Sync Failed: {str(e)}")

    # ── Empty state ───────────────────────────────────────────────────────
    if df.empty:
        render_header("")
        st.info(
            "👋 Welcome! Enter your `_ncfa` token in the sidebar and "
            "click **Sync New Games** to fetch your duels history."
        )
        return

    # ── Process & render ──────────────────────────────────────────────────
    df = apply_timezone(df, tz_hours, tz_minutes)
    render_header(player_nick)

    # Filters
    filters = render_filters(df)
    filtered_df = df.copy()

    if filters.get("modes"):
        filtered_df = filtered_df[filtered_df["Game Mode"].isin(filters["modes"])]
    if filters.get("maps"):
        filtered_df = filtered_df[filtered_df["Map Name"].isin(filters["maps"])]
    if filters.get("date_range") and len(filters["date_range"]) == 2:
        start, end = filters["date_range"]
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start) &
            (filtered_df["Date"].dt.date <= end)
        ]

    if filtered_df.empty:
        st.warning("No games match the current filters.")
        return

    # Metrics
    stats = get_stats_overview(filtered_df)
    render_metric_cards(stats)

    st.write("")  # spacer

    # Tabs
    t_over, t_geo, t_anal, t_data = st.tabs(
        ["📊 Overview", "🗺️ Geography", "📈 Deep Dive", "📄 Raw Data"]
    )

    with t_over:
        tab_overview.render(filtered_df)
    with t_geo:
        tab_geography.render(filtered_df)
    with t_anal:
        tab_analysis.render(filtered_df)
    with t_data:
        tab_data.render(filtered_df)


if __name__ == "__main__":
    main()
