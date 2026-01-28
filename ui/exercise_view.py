"""
Exercise view for the UI layer.

Displays exercise-level KPIs, progress indicators,
time trends, and comparative analysis.
"""

from typing import Dict
import pandas as pd
import streamlit as st


class ExerciseView:
    """
    UI view responsible for presenting exercise-level insights.

    Data sources:
    - exercises_metrics: aggregated metrics per exercise
    - sets_df: raw set-level data (for time-based trends only)

    Responsibilities:
    - exercise selector
    - KPI summary
    - progress indicators
    - trends visualization
    - comparative table
    """

    def __init__(self, exercises_metrics: Dict, sets_df: pd.DataFrame):
        self.exercises_metrics = exercises_metrics
        self.sets_df = sets_df

    def render(self) -> None:
        """Render the Exercises view."""
        st.header("Exercises")
        per_exercise = self.exercises_metrics.get("per_exercise", {})
        exercises_df = pd.DataFrame(per_exercise).T.reset_index(drop=True)

        if exercises_df.empty:
            st.info("No exercise data available.")
            return

        # ---------- Exercise selector ----------
        exercise_name = st.selectbox("Select exercise", options=exercises_df["exercise_name"].tolist(),)
        exercise_row = exercises_df[exercises_df["exercise_name"] == exercise_name].iloc[0]
        exercise = exercise_row.to_dict()

        st.divider()

        # ---------- KPI: primary ----------
        st.subheader("Performance Overview")

        kpi_cols = st.columns(5)

        kpi_cols[0].metric("Total Sets", exercise["total_sets"])
        kpi_cols[1].metric("Sessions", exercise["sessions_count"])
        kpi_cols[2].metric("Total Volume", int(exercise["total_volume"]))
        kpi_cols[3].metric("Max Weight", round(exercise["max_weight"], 1))
        kpi_cols[4].metric("Estimated 1RM (max)", round(exercise["estimated_1rm_max"], 1))

        st.divider()

        # ---------- KPI: secondary ----------
        st.subheader("Training Characteristics")

        sec_cols = st.columns(4)

        avg_reps_per_set = (exercise["total_reps"] / exercise["total_sets"] if exercise["total_sets"] else None)

        sec_cols[0].metric("Avg Weight", round(exercise["avg_weight"], 2))
        sec_cols[1].metric("Avg Reps / Set", round(avg_reps_per_set, 1) if avg_reps_per_set else "—")
        sec_cols[2].metric("Avg RIR",round(exercise["avg_rir"], 2) if exercise["avg_rir"] is not None else "—")
        sec_cols[3].metric("Sets to Failure", exercise["sets_to_failure"])

        st.divider()

        # ---------- Progress indicators ----------
        st.subheader("Progress")

        prog_cols = st.columns(2)

        prog_cols[0].metric(
            "Strength Trend (1RM)",
            round(exercise["estimated_1rm_max"], 1),
            delta=round(exercise["strength_trend_1rm"], 1),
        )

        prog_cols[1].metric(
            "Volume Trend",
            int(exercise["total_volume"]),
            delta=int(exercise["volume_trend"]),
        )

        st.divider()

        # ---------- Trends ----------
        st.subheader("Trends")

        exercise_sets = self.sets_df[self.sets_df["ExerciseName"] == exercise_name].copy()

        if exercise_sets.empty:
            st.info("No time-series data available for this exercise.")
            return

        exercise_sets["SessionDate"] = pd.to_datetime(exercise_sets["SessionDate"])

        trend_df = (exercise_sets.groupby("SessionDate").agg(
                Volume=("Volume", "sum"),
                MaxWeight=("Weight", "max"),
            ).reset_index().sort_values("SessionDate"))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Volume per Session**")
            st.line_chart(trend_df.set_index("SessionDate")[["Volume"]],height=300)

        with col2:
            st.markdown("**Max Weight per Session**")
            st.line_chart(trend_df.set_index("SessionDate")[["MaxWeight"]],height=300)

        st.divider()
        
        # ---------- Comparative table ----------
        st.subheader("Exercise Comparison")

        compare_df = exercises_df[
            [
                "exercise_name",
                "total_sets",
                "sessions_count",
                "total_volume",
                "estimated_1rm_max",
                "avg_rir",
                "avg_sets_per_session",
            ]
        ].rename(columns={
            "exercise_name": "Exercise",
            "total_sets": "Total Sets",
            "sessions_count": "Sessions",
            "total_volume": "Total Volume",
            "estimated_1rm_max": "Estimated 1RM",
            "avg_rir": "Avg RIR",
            "avg_sets_per_session": "Avg Sets / Session",
        })

        def highlight_selected(row):
            if row["Exercise"] == exercise_name:
                return ["background-color: #2a2a2a"] * len(row)
            return [""] * len(row)

        st.dataframe(
            compare_df
            .sort_values("Total Volume", ascending=False)
            .style.apply(highlight_selected, axis=1),
            column_config={
                "Estimated 1RM": st.column_config.NumberColumn(format="%.2f"),
                "Avg RIR": st.column_config.NumberColumn(format="%.2f"),
                "Avg Sets / Session": st.column_config.NumberColumn(format="%.2f"),
                "Total Volume": st.column_config.NumberColumn(format="%.0f"),
            },
            width="stretch",
        )
