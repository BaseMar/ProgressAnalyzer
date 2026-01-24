"""
Exercise view for the UI layer.

Displays exercise-level KPIs and trends based on:
- aggregated exercise metrics (metrics["exercises"])
- raw sets dataframe (sets_df) for time-based trends
"""

from typing import Dict
import pandas as pd
import streamlit as st

from ui.utils.exercises_df import build_exercises_df


def estimate_1rm(weight: float, reps: int) -> float:
    """
    Estimate one-repetition maximum (1RM) using Epley formula.

    Parameters
    ----------
    weight : float
        Weight used in the set.
    reps : int
        Number of repetitions.

    Returns
    -------
    float
        Estimated 1RM value.
    """
    return weight * (1 + reps / 30)


class ExerciseView:
    """
    UI view responsible for presenting exercise-level insights.

    Responsibilities:
    - exercise selector
    - KPI summary per exercise
    - volume and strength trends over time
    """

    def __init__(self, exercises_metrics: Dict, sets_df: pd.DataFrame):
        self.exercises_metrics = exercises_metrics
        self.sets_df = sets_df

    def render(self) -> None:
        """Render the Exercises view."""
        st.header("Exercises")

        exercises_df = build_exercises_df(self.exercises_metrics, self.sets_df)

        if exercises_df.empty:
            st.info("No exercise data available.")
            return

        # ---Exercise selector---
        exercise_name = st.selectbox("Select exercise",options=exercises_df["exercise_name"].tolist(),)
        exercise_row = exercises_df[exercises_df["exercise_name"] == exercise_name].iloc[0]

        # ---KPI row---
        kpi_cols = st.columns(5)

        kpi_cols[0].metric("Total sets", int(exercise_row["total_sets"]))
        kpi_cols[1].metric("Sessions", int(exercise_row["sessions_count"]))
        kpi_cols[2].metric("Estimated 1RM (max)",round(exercise_row["estimated_1rm_max"], 1),)
        kpi_cols[3].metric("Total volume",int(exercise_row["total_volume"]),)
        kpi_cols[4].metric("Max weight",round(exercise_row["max_weight"], 1),)

        # ---------- Trends ----------
        st.subheader("Trends")

        exercise_sets = self.sets_df[self.sets_df["ExerciseName"] == exercise_name].copy()

        if exercise_sets.empty:
            st.info("No set-level data available for this exercise.")
            return

        exercise_sets["SessionDate"] = pd.to_datetime(exercise_sets["SessionDate"])
        exercise_sets["Estimated1RM"] = exercise_sets.apply(lambda r: estimate_1rm(r["Weight"], r["Repetitions"]),axis=1)
        trend_df = (exercise_sets.groupby("SessionDate").agg(Volume=("Volume", "sum"),Estimated1RM=("Estimated1RM", "max")).reset_index().sort_values("SessionDate"))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Volume per session**")
            st.line_chart(trend_df.set_index("SessionDate")[["Volume"]],height=300)

        with col2:
            st.markdown("**Strength (estimated 1RM)**")
            st.line_chart(trend_df.set_index("SessionDate")[["Estimated1RM"]],height=300)

        # ---Comparative table---
        st.subheader("Exercise comparison")

        compare_df = exercises_df[[
            "exercise_name",
            "total_sets",
            "sessions_count",
            "total_volume",
            "max_weight",
            "estimated_1rm_max",
            "avg_sets_per_session",
        ]].rename(columns={
            "exercise_name": "Exercise",
            "total_sets": "Total sets",
            "sessions_count": "Sessions",
            "total_volume": "Total volume",
            "max_weight": "Max weight",
            "estimated_1rm_max": "Estimated 1RM",
            "avg_sets_per_session": "Avg sets / session",
        })

        # highlight selected exercise
        def highlight_selected(row):
            if row["Exercise"] == exercise_name:
                return ["background-color: #2a2a2a"] * len(row)
            return [""] * len(row)

        st.dataframe(compare_df.sort_values("Total volume", ascending=False).style.format(
            {
                "Total sets": "{:.0f}",
                "Sessions": "{:.0f}",
                "Total volume": "{:.0f}",
                "Max weight": "{:.1f}",
                "Estimated 1RM": "{:.1f}",
                "Avg sets / session": "{:.2f}",
            }).apply(highlight_selected, axis=1),width='stretch')
