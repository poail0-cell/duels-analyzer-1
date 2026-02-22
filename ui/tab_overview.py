"""Overview Dashboard tab — performance timeline, streaks, rating deltas."""

import streamlit as st
import plotly.express as px
from src.analytics import rating_history, rating_change_per_game, streaks, games_played_over_time
from ui.styles import PLOTLY_THEME


def render(df):
    st.markdown("### Performance Overview")

    # ── Streak cards ──────────────────────────────────────────────────────
    streak_data = streaks(df)
    scols = st.columns(4)
    with scols[0]:
        emoji = "🔥" if streak_data["current_type"] == "Win" else "❄️"
        st.metric(
            f"Current Streak {emoji}",
            f"{streak_data['current_streak']} {streak_data['current_type']}{'s' if streak_data['current_streak'] != 1 else ''}",
        )
    with scols[1]:
        st.metric("Longest Win Streak", f"{streak_data['longest_win']} 🏆")
    with scols[2]:
        st.metric("Longest Loss Streak", f"{streak_data['longest_loss']} 💀")
    with scols[3]:
        # Quick round win rate
        rwr = df["Round Won"].mean() * 100 if not df.empty else 0
        st.metric("Round Win Rate", f"{rwr:.1f}%")

    st.write("")  # spacer

    # ── Score & rating charts side by side ─────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        df_sorted = df.sort_values("Date").copy()
        df_sorted["Rolling Score"] = df_sorted["Your Score"].rolling(window=50).mean()
        fig = px.line(df_sorted, x="Date", y="Rolling Score", title="Average Score (50-Round Moving Avg)")
        fig.update_layout(**PLOTLY_THEME["layout"])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        r_hist = rating_history(df)
        if not r_hist.empty:
            fig2 = px.line(r_hist, x="Date", y="Your Rating", title="Rating Progression")
            fig2.update_layout(**PLOTLY_THEME["layout"])
            fig2.update_traces(line=dict(color="#00c6ff"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No rating progression data available.")

    # ── Rating change per game ────────────────────────────────────────────
    st.markdown("### Rating Change Per Game")
    rc = rating_change_per_game(df)
    if not rc.empty:
        rc_clean = rc.dropna(subset=["Rating Change"])
        colors = rc_clean["Rating Change"].apply(lambda x: "gain" if x >= 0 else "loss")
        fig_rc = px.bar(
            rc_clean, x="Date", y="Rating Change", color=colors,
            color_discrete_map={"gain": "#00c6ff", "loss": "#ff4b5c"},
            title="Rating Δ Per Game",
        )
        fig_rc.update_layout(**PLOTLY_THEME["layout"], showlegend=False, bargap=0.1)
        st.plotly_chart(fig_rc, use_container_width=True)
    else:
        st.info("Not enough games to compute rating changes.")

    # ── Match activity ────────────────────────────────────────────────────
    st.markdown("### Match Activity")
    period = st.radio("Group by", ("Week", "Month", "Year"), horizontal=True, key="overview_period")
    period_map = {"Week": "W", "Month": "M", "Year": "Y"}
    gp = games_played_over_time(df, period_map[period])
    if not gp.empty:
        fig3 = px.bar(gp, x="Period", y="Games Played", title=f"Games Played Per {period}")
        fig3.update_layout(**PLOTLY_THEME["layout"], bargap=0.15)
        st.plotly_chart(fig3, use_container_width=True)
