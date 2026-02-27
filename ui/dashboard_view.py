from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.utils.ui_helpers import chart_label, fmt_num, line_chart, page_title, section_header


def _set_pills(ex_df: pd.DataFrame) -> str:
    """Return HTML string of set pill badges for one exercise."""
    return "".join(
        f'<span class="set-pill">{row["Repetitions"]} × {row["Weight"]:g} kg</span>'
        for _, row in ex_df.sort_values("SetNumber").iterrows()
    )


class DashboardView:
    def __init__(self, metrics: dict, sets_df: pd.DataFrame) -> None:
        self.metrics = metrics
        self.sets_df = sets_df

    def render(self) -> None:
        self._render_title()
        self._render_kpis()
        self._render_trends()
        self._render_history()

    def _render_title(self) -> None:
        page_title("Overview", "Workout Dashboard")

    def _render_kpis(self) -> None:
        g = self.metrics.get("sessions", {}).get("global", {})

        section_header("Performance Snapshot")

        cols = st.columns(5)
        cols[0].metric("Avg Intensity", f"{fmt_num(g.get('avg_intensity'), 1)} %" if g.get("avg_intensity") is not None else "—")
        cols[1].metric("Sessions / Week", fmt_num(g.get("avg_sessions_per_week"), 1) if g.get("avg_sessions_per_week") else "—")
        cols[2].metric("Avg Volume / Session", f"{fmt_num(g.get('avg_volume_per_session'), 0)} kg" if g.get("avg_volume_per_session") else "—")
        cols[3].metric("Avg Sets / Session", fmt_num(g.get("avg_sets_per_session"), 1) if g.get("avg_sets_per_session")  else "—")
        cols[4].metric("Avg Duration", f"{fmt_num(g.get('avg_session_duration'), 0)} min" if g.get("avg_session_duration")  else "—")

    def _render_trends(self) -> None:
        per_session = self.metrics.get("sessions", {}).get("per_session", {})
        rows = [
            {
                "Date": s["session_date"],
                "Volume (kg)": s.get("total_volume"),
                "Duration (min)": s.get("duration_minutes"),
            }
            for s in per_session.values()
            if s.get("session_date") is not None
        ]

        section_header("Session Trends")

        if not rows:
            st.info("No trend data available yet.")
            return

        trend_df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
        col1, col2 = st.columns(2)

        with col1:
            chart_label("Volume per Session")
            line_chart(trend_df, "Volume (kg)")

        with col2:
            chart_label("Session Duration")
            line_chart(trend_df, "Duration (min)")

    def _render_history(self) -> None:
        section_header("Session History")

        df = self.sets_df.copy()
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])
        df = df.sort_values("SessionDate", ascending=False)

        for session_date, session_df in df.groupby("SessionDate", sort=False):
            total_volume = (session_df["Repetitions"] * session_df["Weight"]).sum()
            total_sets      = len(session_df)
            exercises_count = session_df["ExerciseName"].nunique()
            volume_str      = f"{total_volume:,.0f}".replace(",", "\u202f")

            label = (
                f"{session_date.strftime('%d %b %Y')}   ·   "
                f"{total_sets} sets   ·   "
                f"{exercises_count} exercises   ·   "
                f"{volume_str} kg"
            )

            with st.expander(label, icon=":material/event:"):
                for exercise, ex_df in session_df.groupby("ExerciseName"):
                    st.markdown(
                        f'<p class="exercise-label">{exercise}</p>'
                        f'<div class="set-pills">{_set_pills(ex_df)}</div>', unsafe_allow_html=True)
                st.markdown('<hr class="exercise-divider">', unsafe_allow_html=True)
