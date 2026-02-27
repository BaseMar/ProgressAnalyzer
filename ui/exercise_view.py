"""
Exercise view for the UI layer.

Displays exercise-level KPIs, time trends, and comparative analysis.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from metrics.utils.strength import estimate_1rm
from ui.utils.exercise_table import render_exercise_table
from ui.utils.ui_helpers import chart_label, fmt_num, line_chart, page_title, section_header


class ExerciseView:
    """
    UI view for exercise-level insights.

    Data sources
    ------------
    exercises_metrics : aggregated metrics per exercise
    sets_df           : raw set-level data (used for time-based trends)
    """

    def __init__(self, exercises_metrics: Dict, sets_df: pd.DataFrame) -> None:
        self.exercises_metrics = exercises_metrics
        self.sets_df = sets_df

    def render(self) -> None:
        page_title("Exercises", "Exercise Library")

        per_exercise = self.exercises_metrics.get("per_exercise", {})
        exercises_df = pd.DataFrame(per_exercise).T.reset_index(drop=True)

        if exercises_df.empty:
            st.info("No exercise data available.")
            return

        self._render_selector(exercises_df)

    # Private sections

    def _render_selector(self, exercises_df: pd.DataFrame) -> None:
        exercise_name = st.selectbox("Select exercise", options=exercises_df["exercise_name"].tolist())
        exercise = exercises_df[exercises_df["exercise_name"] == exercise_name].iloc[0].to_dict()

        self._render_kpis(exercise)
        self._render_trends(exercise_name)
        self._render_comparison(exercises_df, exercise_name)

    def _render_kpis(self, exercise: dict) -> None:
        section_header("Performance Overview")

        cols = st.columns(5)
        cols[0].metric("Total Sets", exercise["total_sets"])
        cols[1].metric("Sessions", exercise["sessions_count"])
        cols[2].metric("Total Volume", f"{fmt_num(exercise['total_volume'], 0)} kg")
        cols[3].metric("Max Weight", f"{fmt_num(exercise['max_weight'], 1)} kg")
        cols[4].metric("Est. 1RM", f"{fmt_num(exercise['estimated_1rm_max'], 1)} kg")

    def _render_trends(self, exercise_name: str) -> None:
        section_header("Trends")

        exercise_sets = self.sets_df[self.sets_df["ExerciseName"] == exercise_name].copy()

        if exercise_sets.empty:
            st.info("No time-series data available for this exercise.")
            return

        exercise_sets["SessionDate"] = pd.to_datetime(exercise_sets["SessionDate"])
        exercise_sets["Estimated1RM"] = exercise_sets.apply(lambda r: estimate_1rm(r["Weight"], r["Repetitions"]), axis=1)

        trend_df = (
            exercise_sets
            .groupby("SessionDate")
            .agg(
                Volume=("Volume", "sum"),
                Estimated1RM=("Estimated1RM", "mean"),
            )
            .reset_index()
            .sort_values("SessionDate")
            .set_index("SessionDate")
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
                "exercise_name":        "Exercise",
                "total_sets":           "Total Sets",
                "sessions_count":       "Sessions",
                "total_volume":         "Total Volume",
                "estimated_1rm_max":    "Est. 1RM",
                "avg_rir":              "Avg RIR",
                "avg_sets_per_session": "Avg Sets / Session",
            })
            .sort_values("Total Volume", ascending=False)
            .reset_index(drop=True)
        )

        render_exercise_table(compare_df, selected=exercise_name)
