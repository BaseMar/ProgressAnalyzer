"""
Dashboard View

Main training dashboard with session-level KPIs, trends, and history.

Responsibilities:
  - Render global training metrics (avg intensity, sessions/week, volume)
  - Display volume and duration trends over time
  - Show session history with exercise breakdowns

All metrics are pre-computed; this view only handles presentation.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.utils.ui_helpers import chart_label, format_number, line_chart, page_title, section_header


def _set_pills(ex_df: pd.DataFrame) -> str:
    """Render set card badges for display in session history.
    
    Args:
        ex_df: DataFrame of sets for an exercise
    
    Returns:
        HTML string with set pill badges (reps × weight)
    """
    return "".join(
        f'<span class="set-pill">{row["Repetitions"]} × {row["Weight"]:g} kg</span>'
        for _, row in ex_df.sort_values("SetNumber").iterrows())


class DashboardView:
    """UI view for the main training dashboard.
    
    Displays:
    - Global training KPIs (intensity, frequency, volume, sets)
    - Session trend charts (volume over time, duration over time)
    - Expandable detailed session history with per-exercise breakdowns
    
    Data:
    - metrics: Pre-computed session-level and global metrics
    - sets_df: Raw set data for detailed session rendering
    """

    def __init__(self, metrics: dict, sets_df: pd.DataFrame) -> None:
        """Initialize with pre-computed metrics and raw set data.
        
        Args:
            metrics: Dictionary with keys 'sessions', 'exercises', 'progress', 'fatigue', 'body'
            sets_df: DataFrame with columns: SessionDate, ExerciseName, Weight, Repetitions, SetNumber
        """
        self.metrics = metrics
        self.sets_df = sets_df

    def render(self) -> None:
        """Render the complete dashboard view."""
        self._render_title()
        self._render_kpis()
        self._render_trends()
        self._render_history()

    def _render_title(self) -> None:
        """Render page header."""
        page_title("Overview", "Workout Dashboard")

    def _render_kpis(self) -> None:
        """Render global training KPIs."""
        g = self.metrics.get("sessions", {}).get("global", {})

        section_header("Performance Snapshot")

        cols = st.columns(5)
        cols[0].metric("Avg Intensity", f"{format_number(g.get('avg_intensity'), 1)} %" if g.get("avg_intensity") is not None else "—")
        cols[1].metric("Sessions / Week", format_number(g.get("avg_sessions_per_week"), 1) if g.get("avg_sessions_per_week") else "—")
        cols[2].metric("Avg Volume / Session", f"{format_number(g.get('avg_volume_per_session'), 0)} kg" if g.get("avg_volume_per_session") else "—")
        cols[3].metric("Avg Sets / Session",format_number(g.get("avg_sets_per_session"), 1) if g.get("avg_sets_per_session") else "—")
        cols[4].metric("Avg Duration",f"{format_number(g.get('avg_session_duration'), 0)} min" if g.get("avg_session_duration") else "—")

    def _render_trends(self) -> None:
        """Render session trend charts (volume and duration over time)."""
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
        """Render expandable session history with exercise details."""
        section_header("Session History")

        df = self.sets_df.copy()
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])
        df = df.sort_values("SessionDate", ascending=False)

        for session_date, session_df in df.groupby("SessionDate", sort=False):
            total_volume = (session_df["Repetitions"] * session_df["Weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["ExerciseName"].nunique()
            volume_str = f"{total_volume:,.0f}".replace(",", "\u202f")

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
                        f'<div class="set-pills">{_set_pills(ex_df)}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<hr class="exercise-divider">', unsafe_allow_html=True)
