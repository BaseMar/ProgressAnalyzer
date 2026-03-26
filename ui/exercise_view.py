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

from metrics.utils.strength import estimate_1rm
from ui.utils.exercise_table import render_exercise_table
from ui.utils.ui_helpers import chart_label, format_number, line_chart, page_title, section_header


class ExerciseView:
    """UI view for exercise-level insights and trends.
    
    Displays:
    - Exercise-level KPIs (total sets, sessions, volume, max weight, estimated 1RM)
    - Strength trends over time (volume per session, average 1RM per session)
    - Comparative table of all exercises ranked by total volume
    
    Data Sources:
    - exercises_metrics: Pre-computed metrics per exercise
    - sets_df: Raw set-level data for calculating time-series trends
    """

    def __init__(self, exercises_metrics: Dict, sets_df: pd.DataFrame) -> None:
        """Initialize with pre-computed exercise metrics and raw set data.
        
        Args:
            exercises_metrics: Dictionary with 'per_exercise' key mapping exercise IDs to metrics
            sets_df: DataFrame with columns: ExerciseName, session_date, Weight, repetitions, Volume
        """
        self.exercises_metrics = exercises_metrics
        self.sets_df = sets_df

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

        cols = st.columns(5)
        cols[0].metric("Total Sets", exercise["total_sets"])
        cols[1].metric("Sessions", exercise["sessions_count"])
        cols[2].metric("Total Volume", f"{format_number(exercise['total_volume'], 0)} kg")
        cols[3].metric("Max Weight", f"{format_number(exercise['max_weight'], 1)} kg")
        cols[4].metric("Est. 1RM", f"{format_number(exercise['estimated_1rm_max'], 1)} kg")

    def _render_trends(self, exercise_name: str) -> None:
        """Render strength trend charts (volume and 1RM over time)."""
        section_header("Trends")

        exercise_sets = self.sets_df[self.sets_df["exercise_name"] == exercise_name].copy()

        if exercise_sets.empty:
            st.info("No time-series data available for this exercise.")
            return

        exercise_sets["session_date"] = pd.to_datetime(exercise_sets["session_date"])
        exercise_sets["Estimated1RM"] = exercise_sets.apply(lambda r: estimate_1rm(r["weight"], r["repetitions"]), axis=1)

        trend_df = (
            exercise_sets
            .groupby("session_date")
            .agg(
                Volume=("volume", "sum"),
                Estimated1RM=("Estimated1RM", "mean"),
            )
            .reset_index()
            .sort_values("session_date")
            .set_index("session_date")
        )
        trend_df["Estimated1RM"] = trend_df["Estimated1RM"].round(2)

        col1, col2 = st.columns(2)
        with col1:
            chart_label("Volume per Session")
            line_chart(trend_df, "Volume")
        with col2:
            chart_label("Avg 1RM per Session")
            line_chart(trend_df, "Estimated1RM")

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
            ]]
            .rename(columns={
                "exercise_name": "Exercise",
                "total_sets": "Total Sets",
                "sessions_count": "Sessions",
                "total_volume": "Total Volume",
                "estimated_1rm_max": "Est. 1RM",
                "avg_rir": "Avg RIR",
                "avg_sets_per_session": "Avg Sets / Session",
            })
            .sort_values("Total Volume", ascending=False)
            .reset_index(drop=True)
        )

        render_exercise_table(compare_df, selected=exercise_name)
