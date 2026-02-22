"""Analysis deep dive tab — distributions, comparisons, round analysis, NMPZ."""

import streamlit as st
import plotly.express as px
import pandas as pd
from src.analytics import stats_by_round, stats_by_country, binned_metrics, head_to_head
from ui.styles import PLOTLY_THEME


def render(df):
    st.markdown("### Analytical Deep Dive")

    # ── Score distribution & scatter ──────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Score Distribution")
        fig_hist = px.histogram(df, x="Your Score", nbins=50, color_discrete_sequence=["#00c6ff"])
        fig_hist.update_layout(**PLOTLY_THEME["layout"], bargap=0.05)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        st.markdown("#### Score vs Distance")
        plot_df = df.sample(n=min(len(df), 2000)) if len(df) > 2000 else df
        fig_scatter = px.scatter(
            plot_df, x="Your Distance", y="Your Score",
            hover_data=["Country", "Round Number"],
            color_discrete_sequence=["#00c6ff"], opacity=0.5,
        )
        fig_scatter.update_layout(**PLOTLY_THEME["layout"])
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Per-round analysis ────────────────────────────────────────────────
    st.markdown("#### Performance By Round Number")
    by_round = stats_by_round(df)
    if not by_round.empty:
        round_metric = st.radio(
            "Round metric", ("Your Score", "Win Rate", "Distance", "Score Difference"),
            horizontal=True, key="round_metric",
        )
        fig_round = px.bar(
            by_round, x="Round Number", y=round_metric,
            color=round_metric, color_continuous_scale="Tealgrn",
            title=f"Avg {round_metric} by Round",
        )
        fig_round.update_layout(**PLOTLY_THEME["layout"])
        st.plotly_chart(fig_round, use_container_width=True)

    # ── Binned histogram over time ────────────────────────────────────────
    st.markdown("#### Metrics Over Time (Binned)")
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        bin_metric = st.selectbox(
            "Metric", ["Your Score", "Score Difference", "Your Distance", "Round Won"],
            key="bin_metric",
        )
    with bcol2:
        bin_period = st.radio("Bin by", ("Week", "Month", "Year"), horizontal=True, key="bin_period")

    period_map = {"Week": "W", "Month": "M", "Year": "Y"}
    binned = binned_metrics(df, bin_metric, period_map[bin_period])
    if not binned.empty:
        fig_bin = px.bar(binned, x="Period", y=bin_metric, title=f"Avg {bin_metric} per {bin_period}")
        fig_bin.update_layout(**PLOTLY_THEME["layout"], bargap=0.1)
        st.plotly_chart(fig_bin, use_container_width=True)

    # ── Country variance box plot ─────────────────────────────────────────
    st.markdown("#### Score Variance by Country (Box Plot)")
    top_15 = df["Country"].value_counts().nlargest(15).index
    box_df = df[df["Country"].isin(top_15)]
    fig_box = px.box(
        box_df, x="Country", y="Your Score", color="Country",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig_box.update_layout(**PLOTLY_THEME["layout"], showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    # ── Metric comparison scatter ─────────────────────────────────────────
    st.markdown("#### Country Metric Comparison")
    country_agg = stats_by_country(df)
    country_agg = country_agg[country_agg["Rounds"] >= 3]

    if not country_agg.empty:
        options = ["Your Score", "Opponent Score", "Score Difference", "Win Rate", "Distance", "Rounds"]
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            choice_x = st.selectbox("X axis", options, index=0, key="cmp_x")
        with mcol2:
            choice_y = st.selectbox("Y axis", options, index=3, key="cmp_y")
        with mcol3:
            choice_c = st.selectbox("Color by", options, index=5, key="cmp_c")
        show_avg = st.checkbox("Show average lines", value=True, key="cmp_avg")

        fig_cmp = px.scatter(
            country_agg, x=choice_x, y=choice_y, color=choice_c,
            hover_name="Country", color_continuous_scale="RdBu",
            text=country_agg["Country"].where(country_agg.index % 5 == 0, ""),
        )
        fig_cmp.update_traces(textposition="top center")
        if show_avg:
            fig_cmp.add_hline(y=country_agg[choice_y].mean(), line_dash="dot", line_color="#4CAF50")
            fig_cmp.add_vline(x=country_agg[choice_x].mean(), line_dash="dot", line_color="#4CAF50")
        fig_cmp.update_layout(**PLOTLY_THEME["layout"], width=700, height=700)
        st.plotly_chart(fig_cmp, use_container_width=False)

    # ── Moving vs No-Move vs NMPZ comparison ──────────────────────────────
    st.markdown("#### Moving vs No-Move vs NMPZ")
    move_labels = []
    move_scores = []

    moving_df = df[df["Moving"] == True]
    nm_df = df[df["Moving"] == False]
    nmpz_df = df[(df["Moving"] == False) & (df["Zooming"] == False)]

    for label, subset in [("Moving", moving_df), ("No Move", nm_df), ("NMPZ", nmpz_df)]:
        if not subset.empty:
            move_labels.append(label)
            move_scores.append({
                "Type": label,
                "Avg Score": subset["Your Score"].mean(),
                "Win Rate": subset["Round Won"].mean() * 100,
                "Avg Distance": subset["Your Distance"].mean(),
                "Rounds": len(subset),
            })

    if move_scores:
        move_df = pd.DataFrame(move_scores)
        st.dataframe(move_df, hide_index=True, use_container_width=True)

        fig_move = px.bar(
            move_df, x="Type", y=["Avg Score", "Win Rate"],
            barmode="group", color_discrete_sequence=["#00c6ff", "#ff4b5c"],
        )
        fig_move.update_layout(**PLOTLY_THEME["layout"])
        st.plotly_chart(fig_move, use_container_width=True)
    else:
        st.info("Need data for at least one game type.")

    # ── Head-to-head ──────────────────────────────────────────────────────
    st.markdown("#### Head-to-Head (Repeat Opponents)")
    h2h = head_to_head(df)
    if not h2h.empty:
        st.dataframe(
            h2h[["Opponent Country", "Games", "Wins", "Losses", "Your Score", "Opponent Score"]].head(15),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("No repeat opponents found.")
