"""Geography tab — maps, country mastery, opponent analysis."""

import streamlit as st
import plotly.express as px
from src.analytics import stats_by_country, stats_by_opponent_country
from ui.styles import PLOTLY_THEME


def render(df):
    country_stats = stats_by_country(df)
    filtered_stats = country_stats[country_stats["Rounds"] >= 3]

    # ── Metric selector ───────────────────────────────────────────────────
    metric = st.radio(
        "Metric",
        ("Your Score", "Win Rate", "Distance", "Score Difference"),
        horizontal=True,
        key="geo_metric",
    )

    # ── Choropleth map ────────────────────────────────────────────────────
    st.markdown("### World Mastery")
    color_scale = "Turbo" if metric != "Distance" else "Turbo_r"
    fig = px.choropleth(
        filtered_stats,
        locations="Country", locationmode="country names",
        color=metric, hover_name="Country",
        hover_data={"Rounds": True, "Win Rate": ":.1f"},
        color_continuous_scale=color_scale,
        title=f"Average {metric} by Country (Min 3 rounds)",
    )
    layout = PLOTLY_THEME["layout"].copy()
    layout.update(geo=dict(bgcolor="rgba(0,0,0,0)", showcoastlines=True, coastlinecolor="rgba(255,255,255,0.2)"))
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    # ── Top / weakest tables ──────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"#### Best Countries ({metric})")
        ascending = metric == "Distance"
        top = filtered_stats.sort_values(metric, ascending=ascending).head(10)
        st.dataframe(top[["Country", metric, "Rounds"]], hide_index=True, use_container_width=True)
    with col2:
        st.markdown(f"#### Weakest Countries ({metric})")
        low = filtered_stats.sort_values(metric, ascending=not ascending).head(10)
        st.dataframe(low[["Country", metric, "Rounds"]], hide_index=True, use_container_width=True)

    # ── Opponent country analysis ─────────────────────────────────────────
    st.markdown("### Performance vs Opponent Nationality")
    opp_stats = stats_by_opponent_country(df)
    opp_filtered = opp_stats[opp_stats["Rounds"] >= 3]
    if not opp_filtered.empty:
        fig_opp = px.bar(
            opp_filtered.sort_values(metric, ascending=False).head(20),
            x="Opponent Country", y=metric,
            color=metric, color_continuous_scale=color_scale,
            title=f"{metric} vs Opponent Country (Top 20, Min 3 rounds)",
        )
        fig_opp.update_layout(**PLOTLY_THEME["layout"])
        st.plotly_chart(fig_opp, use_container_width=True)
    else:
        st.info("Not enough opponent data to display.")

    # ── Guess scatter map ─────────────────────────────────────────────────
    st.markdown("### Your Guesses on the Map")
    guess_metric = "Your Score" if metric != "Distance" else "Your Distance"
    sample = df.sample(n=min(len(df), 3000)) if len(df) > 3000 else df
    fig_map = px.scatter_geo(
        sample, lat="Your Latitude", lon="Your Longitude",
        color=guess_metric,
        color_continuous_scale="Turbo_r" if guess_metric == "Your Distance" else "Turbo",
        projection="natural earth",
        title=f"Your Guesses — colored by {guess_metric}",
    )
    fig_map.update_traces(marker=dict(size=4))
    fig_map.update_layout(**PLOTLY_THEME["layout"], geo=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig_map, use_container_width=True)
