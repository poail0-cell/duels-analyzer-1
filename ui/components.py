"""Reusable UI components."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta


def render_header(nick: str):
    """Render the top-level app header."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<h1>⚡ Geo-Duels Analyzer</h1>", unsafe_allow_html=True)
        if nick:
            st.markdown(
                f"#### Welcome back, <span style='color: #00c6ff'>{nick}</span>",
                unsafe_allow_html=True,
            )
    with col2:
        # Use a simple emoji globe instead of an external image URL that may 404
        st.markdown(
            "<div style='text-align:right; font-size:64px; padding-top:10px'>🌍</div>",
            unsafe_allow_html=True,
        )


def render_metric_cards(stats: dict):
    """Show the top-level headline metrics."""
    cols = st.columns(5)
    with cols[0]:
        st.metric("Total Games", stats.get("total_games", 0))
    with cols[1]:
        cr = stats.get("current_rating", 0)
        st.metric("Current Rating", f"{cr:.0f}" if cr else "N/A")
    with cols[2]:
        st.metric("Game Win Rate", f"{stats.get('game_win_rate', 0):.1f}%")
    with cols[3]:
        st.metric("Avg Score / Round", f"{stats.get('avg_score', 0):.0f}")
    with cols[4]:
        st.metric("Avg Distance (km)", f"{stats.get('avg_distance', 0):.0f}")


def render_filters(df: pd.DataFrame) -> dict:
    """Render filter controls and return the selected parameters."""
    if df.empty:
        return {}

    with st.expander("🎛️ Data Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            modes = st.multiselect(
                "Game Mode", df["Game Mode"].unique(), default=list(df["Game Mode"].unique())
            )
        with col2:
            maps = st.multiselect("Map", df["Map Name"].unique(), placeholder="All Maps")
        with col3:
            min_date = df["Date"].min().date() if not df.empty else date.today() - timedelta(days=365)
            max_date = df["Date"].max().date() if not df.empty else date.today()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
            )

    return {"modes": modes, "maps": maps, "date_range": date_range}
