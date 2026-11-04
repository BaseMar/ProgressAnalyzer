"""
Exercise View

Displays exercise-level analysis including KPIs, strength trends, and comparative metrics.

Responsibilities:
  - Render per-exercise performance metrics (volume, max weight, estimated 1RM)
  - Display strength trends over time (volume and estimated 1RM progression)
  - Provide comparative exercise table showing all exercises ranked by volume
  
All calculations are pre-computed in the metrics layer; this view handles presentation only.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from ui.utils.exercise_table import render_exercise_table
from ui.utils.ui_helpers import chart_label, format_number, line_chart, page_title, section_header


class ExerciseView:
    """UI view for exercise-level insights and trends.
    
    Displays:
    - Exercise-level KPIs (total sets, sessions, volume, max weight, estimated 1RM)
    - Descriptive workload and eligible performance trends by session
    - Comparative table of all exercises ranked by total volume
    
    Data Sources:
    - exercises_metrics: Pre-computed metrics per exercise
    - sets_df: Raw set-level data retained for source/history compatibility
    """

    def __init__(self, exercises_metrics: Dict, sets_df: pd.DataFrame) -> None:
        """Initialize with pre-computed exercise metrics and raw set data.
        
        Args:
            exercises_metrics: Dictionary with 'per_exercise' key mapping exercise IDs to metrics
            sets_df: DataFrame with columns: ExerciseName, session_date, Weight, repetitions, Volume
        """
        self.exercises_metrics = exercises_metrics
        self.sets_df = sets_df.loc[~sets_df["is_warmup"].eq(True)].copy() if "is_warmup" in sets_df else sets_df

    def render(self) -> None:
        """Render the complete exercise analysis view."""
        page_title("Exercises", "Exercise Library")

        per_exercise = self.exercises_metrics.get("per_exercise", {})
        exercises_df = pd.DataFrame(per_exercise).T.reset_index(drop=True)

        if exercises_df.empty:
            st.info("No exercise data available.")
            return

        self._render_selector(exercises_df)

    def _render_selector(self, exercises_df: pd.DataFrame) -> None:
        """Render exercise selector dropdown and associated analysis sections."""
        exercise_name = st.selectbox("Select exercise", options=exercises_df["exercise_name"].tolist())
        exercise = exercises_df[exercises_df["exercise_name"] == exercise_name].iloc[0].to_dict()

        self._render_kpis(exercise)
        self._render_trends(exercise_name)
        self._render_comparison(exercises_df, exercise_name)

    def _render_kpis(self, exercise: dict) -> None:
        """Render per-exercise performance snapshot."""
        section_header("Performance Overview")

        is_duration_exercise = bool(exercise.get("total_duration_seconds"))
        cols = st.columns(5)
        cols[0].metric("Total Sets", exercise["total_sets"])
        cols[1].metric("Sessions", exercise["sessions_count"])
        if is_duration_exercise:
            cols[2].metric("Total Time", _format_seconds(exercise.get("total_duration_seconds")))
            cols[3].metric("Best Set", _format_seconds(exercise.get("best_duration_seconds")))
            cols[4].metric("Effective Sets", format_number(exercise.get("effective_sets"), 1))
        else:
            cols[2].metric("Total Volume", f"{format_number(exercise['total_volume'], 0)} kg")
            cols[3].metric("Max Weight", f"{format_number(exercise['max_weight'], 1)} kg")
            cols[4].metric("Est. 1RM", f"{format_number(exercise['estimated_1rm_max'], 1)} kg")

    def _render_trends(self, exercise_name: str) -> None:
        """Render prepared series with the same effort policy as the metrics."""
        section_header("Trends")
        exercise = next((row for row in self.exercises_metrics.get("per_exercise", {}).values()
                         if row["exercise_name"] == exercise_name), None)
        if exercise is None:
            st.info("No time-series data available for this exercise.")
            return
        timed = bool(exercise.get("total_duration_seconds"))
        col1, col2 = st.columns(2)
        with col1:
            chart_label("Session Duration" if timed else "Session Volume")
            self._series(exercise.get("per_session_duration" if timed else "per_session_volume", []),
                         "duration_seconds" if timed else "volume", "Duration (s)" if timed else "Volume (kg)")
        with col2:
            chart_label("Best Set" if timed else "Best eligible e1RM")
            self._series(exercise.get("per_session_best_duration" if timed else "per_session_1rm", []),
                         "duration_seconds" if timed else "estimated_1rm", "Best Set (s)" if timed else "Best e1RM (kg)")
        st.caption("Workload preserves light and unknown-effort logs. Performance trends use eligible ordinary sets or timed work, excluding planned deloads. Sessions on the same day remain separate.")

    @staticmethod
    def _series(points, field, label):
        if not points:
            st.caption("No eligible results for this series yet.")
            return
        frame = pd.DataFrame(points).rename(columns={"date": "Date", field: label})
        frame["Date"] = pd.to_datetime(frame["Date"])
        frame = frame.sort_values(["Date", "session_id"]).set_index("Date")
        line_chart(frame[[label]], label)

    def _render_comparison(self, exercises_df: pd.DataFrame, exercise_name: str) -> None:
        """Render comparative table of all exercises ranked by volume."""
        section_header("Exercise Comparison")

        compare_df = (
            exercises_df[[
                "exercise_name",
                "total_sets",
                "sessions_count",
                "total_volume",
                "estimated_1rm_max",
                "avg_rir",
                "avg_sets_per_session",
                "body_part",
                "muscle_target_summary",
            ]]
            .rename(columns={
                "exercise_name": "Exercise",
                "total_sets": "Total Sets",
                "sessions_count": "Sessions",
                "total_volume": "Total Volume",
                "estimated_1rm_max": "Est. 1RM",
                "avg_rir": "Avg RIR",
                "avg_sets_per_session": "Avg Sets / Session",
                "muscle_target_summary": "Muscle Targets",
            })
            .sort_values("Total Volume", ascending=False)
            .reset_index(drop=True)
        )

        render_exercise_table(compare_df, selected=exercise_name)


def _format_seconds(value: int | float | None) -> str:
    if value is None:
        return "-"

    seconds = int(value)
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}:{remaining_seconds:02d}"
    return f"{seconds}s"
