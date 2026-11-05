"""Compact weekly targets and recorded allocation; methodology lives in README."""
import streamlit as st

from metrics.muscle_distribution import build_weekly_distribution
from ui.utils.ui_helpers import chart_label


def render_weekly_distribution(body_df, period_weeks, period_label, *, weekly_targets=None):
    chart_label("Weekly muscle sets")
    summary = build_weekly_distribution(body_df, period_weeks, weekly_targets)
    display = summary[["Body Part", "Target", "Sets / Week", "Target %"]].rename(
        columns={"Sets / Week": "Recorded / week"})
    st.dataframe(display, hide_index=True, width="stretch", column_config={
        "Target": st.column_config.NumberColumn("Plan target", format="%.1f"),
        "Recorded / week": st.column_config.NumberColumn("Recorded / week", format="%.1f"),
        "Target %": st.column_config.NumberColumn("Plan %", format="%.0f%%"),
    })
    st.caption(f"{period_label} | {period_weeks:.1f} weeks")
    return summary
