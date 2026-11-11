"""Full recorded exercise history with descriptive session means."""

from __future__ import annotations

from collections import Counter
from typing import Dict

import pandas as pd
import streamlit as st

from ui.utils.analysis_kpis import recorded_set_value
from ui.utils.load_charts import mean_load_history_chart
from ui.utils.set_load_inputs import LOAD_LABELS


class ExerciseView:
    """Present the active exercise analysis using precomputed metrics."""

    def __init__(self, exercises_metrics: Dict, *, filters=None) -> None:
        self.exercises_metrics = exercises_metrics
        self.filters = filters

    def render(self) -> None:
        if not self.exercises_metrics.get("per_exercise"):
            st.info("No exercise data available.")
            return
        self._render_selected_exercise()

    def _render_selected_exercise(self):
        items = self.exercises_metrics.get("per_exercise", {})
        if st.session_state.get("analysis_recorded_exercise") not in items:
            st.session_state["analysis_recorded_exercise"] = next(iter(items))
        labels = Counter(item["exercise_name"] for item in items.values())
        selected = st.selectbox(
            "Exercise",
            list(items),
            key="analysis_recorded_exercise",
            format_func=lambda value: (
                items[value]["exercise_name"]
                + (f" - #{value}" if labels[items[value]["exercise_name"]] > 1 else "")
            ),
        )
        exercise = items[selected]
        points = exercise.get("per_set_performance", [])
        if not points:
            st.info("No recorded sets in this period. Choose another period in Filters.")
            return
        with self.filters if self.filters is not None else st.container():
            points = self._select_load_series(points)
        self._render_selected_results(points)

    def _select_load_series(self, points):
        kinds = list(dict.fromkeys(item["load_type"] for item in points))
        kind = (
            st.selectbox(
                "Load convention",
                [None, *kinds],
                format_func=lambda value: (
                    "All load conventions" if value is None else LOAD_LABELS[value]
                ),
                key="recorded_load_convention",
            )
            if len(kinds) > 1
            else kinds[0]
        )
        if kind is not None:
            points = [item for item in points if item["load_type"] == kind]
        units = list(dict.fromkeys(item["unit"] for item in points))
        unit = (
            st.radio("Recorded set type", units, horizontal=True, key="recorded_load_unit")
            if len(units) > 1
            else units[0]
        )
        points = [item for item in points if item["unit"] == unit]
        # The filter controls render into the shared Filters panel; results stay
        # in the page's original position rather than inside that panel.
        return points

    def _render_selected_results(self, points):
        self._render_history_context(points)
        fig = mean_load_history_chart(points)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="recorded_load_history")
        st.caption(
            "Session means describe all logged sets, including light and unknown-effort work. Read repetitions or time together with load; direction alone does not establish improvement."
        )
        if any(item["total_load_kg"] is None for item in points):
            st.caption("Some load values are missing.")
        with st.expander("Recorded sets"):
            fields = [
                "date",
                "quantity",
                "unit",
                "weight",
                "body_mass_kg",
                "assistance_kg",
                "total_load_kg",
                "rir",
            ]
            st.dataframe(
                pd.DataFrame(points)[fields].rename(
                    columns={
                        "date": "Date",
                        "weight": "External kg",
                        "body_mass_kg": "Body mass kg",
                        "assistance_kg": "Assistance kg",
                        "total_load_kg": "Total kg",
                        "quantity": "Reps/seconds",
                    }
                ),
                hide_index=True,
                width="stretch",
            )

    @staticmethod
    def _render_history_context(points):
        if points:
            latest = max(
                points,
                key=lambda item: (
                    pd.Timestamp(item["date"]),
                    item.get("session_order", item["session_id"]),
                    item["workout_exercise_id"],
                    item["set_number"],
                ),
            )
            item = {**latest, "seconds": latest["quantity"], "reps": latest["quantity"]}
            st.caption(
                f"Latest set: {recorded_set_value(item, latest['unit'])} - {latest['date']:%d %b %Y}"
            )
        st.caption(
            f"{len(points)} logged sets across {len({item['session_id'] for item in points})} sessions in this period."
        )
