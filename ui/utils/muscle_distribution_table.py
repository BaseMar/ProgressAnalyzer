"""Compact weekly targets and recorded allocation; methodology lives in README."""

import streamlit as st

from metrics.muscle_distribution import build_weekly_distribution
from ui.utils.ui_helpers import chart_label


def render_weekly_distribution(body_df, period_weeks, period_label, *, weekly_targets=None):
    chart_label("Weekly muscle sets")
    summary = build_weekly_distribution(body_df, period_weeks, weekly_targets)
    parts = summary["Body Part"].tolist()
    if st.session_state.get("analysis_muscle_part") not in parts:
        recorded = summary.loc[summary["Total Sets"] > 0, "Body Part"]
        st.session_state["analysis_muscle_part"] = (
            recorded.iloc[0] if not recorded.empty else parts[0]
        )
    selected = st.selectbox("Muscle group", parts, key="analysis_muscle_part")
    row = summary.loc[summary["Body Part"] == selected].iloc[0]
    recorded, target, coverage = st.columns(3)
    recorded.metric(
        "Recorded sets / week",
        f"{row['Sets / Week']:.1f}",
        help="Weighted dynamic set equivalents, averaged over the selected period. Timed sets are shown separately.",
    )
    target.metric(
        "Plan sets / week",
        f"{row['Target']:.1f}" if weekly_targets is not None else "—",
        help="Reference week of the active plan version effective today.",
    )
    coverage.metric(
        "Plan target logged",
        f"{row['Target %']:.0f}%" if row["Target"] is not None and row["Target"] > 0 else "—",
        help="Recorded weekly set equivalents divided by the plan target. Higher is not automatically better; a zero target has no percentage.",
    )
    display = summary[["Body Part", "Target", "Sets / Week", "Target %"]].rename(
        columns={"Sets / Week": "Recorded / week"}
    )
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "Target": st.column_config.NumberColumn("Plan target", format="%.1f"),
            "Recorded / week": st.column_config.NumberColumn("Recorded / week", format="%.1f"),
            "Target %": st.column_config.NumberColumn("Plan %", format="%.0f%%"),
        },
    )
    return summary
