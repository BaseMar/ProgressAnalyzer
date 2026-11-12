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

    def __init__(
        self, exercises_metrics: Dict, *, filters=None, selection=None, exercise_options=None
    ) -> None:
        self.exercises_metrics = exercises_metrics
        self.filters = filters
        self.selection = selection
        self.options = exercise_options

    def render(self) -> None:
        if not self.exercises_metrics.get("per_exercise") and not self.options:
            st.info(
                "No exercise history yet. Import a workout TXT or enter a workout in History to start."
            )
            return
        self._render_selected_exercise()

    def _render_selected_exercise(self):
        items = self.exercises_metrics.get("per_exercise", {})
        options = (
            self.options
            if self.options is not None
            else {key: item["exercise_name"] for key, item in items.items()}
        )
        if st.session_state.get("analysis_recorded_exercise") not in options:
            saved = st.session_state.get("analysis_exercise_value")
            st.session_state["analysis_recorded_exercise"] = (
                saved if saved in options else next(iter(options))
            )
        labels = Counter(options.values())
        with self.selection if self.selection is not None else st.container():
            selected = st.selectbox(
                "Exercise",
                list(options),
                key="analysis_recorded_exercise",
                format_func=lambda value: (
                    options[value] + (f" - #{value}" if labels[options[value]] > 1 else "")
                ),
            )
            if len(options[selected]) > 80:
                st.caption(options[selected])
        st.session_state["analysis_exercise_value"] = selected
        exercise = items.get(selected, {})
        points = exercise.get("per_set_performance", [])
        if not points:
            st.info(
                "No recorded sets for this exercise in the selected period. Change Analysis period above the tabs."
            )
            if self.filters is not None:
                st.button(
                    "Show all history", on_click=_show_all_history, key="analysis_show_all_history"
                )
            return
        with self.filters if self.filters is not None else st.container():
            points = self._select_load_series(points)
        self._render_selected_results(points)

    def _select_load_series(self, points):
        kinds = list(dict.fromkeys(item["load_type"] for item in points))
        if st.session_state.get("recorded_load_convention") not in (None, *kinds):
            st.session_state["recorded_load_convention"] = None
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
        if st.session_state.get("recorded_load_unit") not in (None, *units):
            st.session_state["recorded_load_unit"] = units[0]
        unit = (
            st.radio(
                "Recorded set type",
                units,
                horizontal=True,
                key="recorded_load_unit",
                format_func=lambda value: "Repetitions" if value == "reps" else "Time (seconds)",
            )
            if len(units) > 1
            else units[0]
        )
        points = [item for item in points if item["unit"] == unit]
        # Optional load/unit controls stay near the selected exercise.
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

    @staticmethod
    def _render_history_context(points):
        latest_description = ""
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
            latest_description = f"Latest set: {recorded_set_value(item, latest['unit'])} - {latest['date']:%d %b %Y}"
        st.caption(
            latest_description
            + f" · {len(points)} logged sets across {len({item['session_id'] for item in points})} sessions in this period."
        )


def _show_all_history():
    st.session_state["analysis_month"] = "All time"
    st.session_state["analysis_period_value"] = "All time"
