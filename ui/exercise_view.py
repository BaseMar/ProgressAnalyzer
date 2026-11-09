"""One recorded exercise: eligible performance, descriptive workload and source sets."""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from metrics.load_metrics import describe_load
from ui.utils.analysis_kpis import recorded_set_value
from ui.utils.load_charts import load_history_chart
from ui.utils.set_load_inputs import LOAD_LABELS
from ui.utils.ui_helpers import line_chart


class ExerciseView:
    """Present the active exercise analysis using precomputed metrics."""

    def __init__(self, exercises_metrics: Dict) -> None:
        self.exercises_metrics = exercises_metrics

    def render(self) -> None:
        if not self.exercises_metrics.get("per_exercise"):
            st.info("No exercise data available.")
            return
        self._render_selected_exercise()

    def _render_selected_exercise(self):
        items = self.exercises_metrics.get("per_exercise", {})
        if st.session_state.get("analysis_recorded_exercise") not in items:
            st.session_state["analysis_recorded_exercise"] = next(iter(items))
        selected = st.selectbox("Recorded exercise", list(items), key="analysis_recorded_exercise",
                                format_func=lambda value: f'{items[value]["exercise_name"]} · #{value}')
        exercise = items[selected]
        timed = bool(exercise.get("total_duration_seconds"))
        question = st.radio("Show", ["Performance", "Workload"], horizontal=True, key="recorded_exercise_series")
        workload = question == "Workload"
        if exercise.get("per_set_performance") and (timed or exercise.get("has_explicit_load")):
            self._render_load_series(exercise, workload)
            return
        self._render_recorded_kpis(exercise, exercise.get("per_set_performance", []))
        field = "duration_seconds" if timed else "volume" if workload else "estimated_1rm"
        key = ("per_session_duration" if workload else "per_session_best_duration") if timed else ("per_session_volume" if workload else "per_session_1rm")
        label = "Seconds" if timed else "Volume (kg)" if workload else "Best eligible e1RM (kg)"
        points = exercise.get(key, [])
        if points:
            st.caption(f'{len(points)} recorded sessions · {exercise["total_sets"]} descriptive sets. Read changes within this exercise only.')
        self._series(points, field, label)
        st.caption("Workload includes light and unknown-effort logs. Performance uses eligible ordinary sets or timed work; planned deloads are excluded. e1RM is an estimate, not a tested maximum.")
        with st.expander("Source sessions"):
            st.dataframe(pd.DataFrame(points), hide_index=True, width="stretch")

    def _render_load_series(self, exercise, workload):
        points = exercise["per_set_performance"]
        kinds = list(dict.fromkeys(item["load_type"] for item in points))
        kind = st.selectbox("Load convention", kinds, format_func=LOAD_LABELS.get,
                            key="recorded_load_convention") if len(kinds) > 1 else kinds[0]
        points = [item for item in points if item["load_type"] == kind]
        units = list(dict.fromkeys(item["unit"] for item in points))
        unit = st.radio("Recorded set type", units, horizontal=True, key="recorded_load_unit") if len(units) > 1 else units[0]
        points = [item for item in points if item["unit"] == unit]
        self._render_recorded_kpis(exercise, points)
        fig = load_history_chart(points, workload=workload)
        if fig is None:
            st.caption("No eligible performance sets yet. Workload includes descriptive logs.")
        else:
            st.plotly_chart(fig, width="stretch", key="recorded_load_history")
        if any(item["total_load_kg"] is None for item in points):
            st.caption("Some load values are missing.")
        with st.expander("Source sets"):
            fields = ["date", "quantity", "unit", "weight", "body_mass_kg", "assistance_kg", "total_load_kg", "rir"]
            st.dataframe(pd.DataFrame(points)[fields].rename(columns={"date": "Date", "weight": "External kg", "body_mass_kg": "Body mass kg",
                "assistance_kg": "Assistance kg", "total_load_kg": "Total kg", "quantity": "Reps/seconds"}),
                hide_index=True, width="stretch")

    @staticmethod
    def _render_recorded_kpis(exercise, points):
        last_set, sets, sessions = st.columns(3)
        if points:
            latest = max(points, key=lambda item: (pd.Timestamp(item["date"]), item.get("session_order", item["session_id"]),
                                                    item["workout_exercise_id"], item["set_number"]))
            item = {**latest, "seconds": latest["quantity"], "reps": latest["quantity"]}
            last_set.metric("Last logged set", recorded_set_value(item, latest["unit"]),
                            help=f'{latest["date"]:%d %b %Y} · {describe_load(latest)}. Recorded work may include light or unknown-effort sets.')
        else:
            last_set.metric("Last logged set", "—")
        sets.metric("Logged sets in period", len(points) if points else exercise["total_sets"])
        sessions.metric("Sessions in period", len({item["session_id"] for item in points}) if points else exercise["sessions_count"])

    @staticmethod
    def _series(points, field, label):
        if not points:
            st.caption("No eligible results for this series yet.")
            return
        frame = pd.DataFrame(points).rename(columns={"date": "Date", field: label})
        frame["Date"] = pd.to_datetime(frame["Date"])
        frame = frame.sort_values(["Date", "session_id"]).set_index("Date")
        line_chart(frame[[label]], label)
