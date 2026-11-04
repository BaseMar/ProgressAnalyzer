"""Analytical overview with optional drill-down and source corrections."""
from calendar import monthrange
from datetime import date, timedelta
from html import escape
import logging
import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from data_manager import DataManager
from metrics.plan_adherence import compatible_set, compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.plan_summary import summarize_plan
from ui.utils.plan_charts import exercise_history_chart, weekly_execution_chart
from ui.utils.ui_helpers import chart_label, section_header
from metrics.training_block import deload_adjusted_input
from ui.next_workout_view import NextWorkoutView

logger = logging.getLogger(__name__)


class PlanAdherenceView:
    def __init__(self, *, manager=None, exercise_names=None, selected_month=None):
        self.dm = manager if manager is not None else DataManager()
        self.names = exercise_names or {}
        self.selected_month = selected_month

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self):
        section_header("Plan overview")
        try:
            if not self.dm.adherence_storage_ready():
                st.info("Plan analysis is not available until setup is complete.")
                return
            plans = {item.plan_id: item for item in self.dm.load_training_plans()}
            if not plans:
                st.info("Add a Training Plan, then link sessions in the calendar to start the analysis.")
                return
            plan_id = st.selectbox("Plan to analyse", list(plans), key="adherence_plan", format_func=lambda value: plans[value].draft.name)
            versions = self.dm.load_training_plan_versions(plan_id)
            if self.selected_month not in (None, "All time"):
                start = date.fromisoformat(f"{self.selected_month}-01")
                end = start.replace(day=monthrange(start.year, start.month)[1])
            else:
                start = min(item.draft.effective_from for item in versions)
                end = max(date.today(), start) + timedelta(days=7)
            data = self.dm.load_plan_adherence(plan_id, start, end)
            history = self.dm.load_plan_performance(plan_id, start, end)
        except SQLAlchemyError:
            logger.exception("Unable to load plan analysis")
            st.error("Plan analysis could not be loaded. Please try again.")
            return
        block_settings = {version.version_id: version.draft.progression for version in versions}
        NextWorkoutView(self.dm, self.names).render(plan_id, versions, history=history)
        section_header("Recorded plan execution")
        report = compute_plan_adherence(deload_adjusted_input(data, block_settings, as_of=date.today()),
                                        as_of=date.today(), settings_by_version=block_settings)
        performance = compute_plan_performance(history, as_of=date.today(), start=start, end=end,
                                             settings_by_version=block_settings)
        overview, summary = summarize_plan(report, performance), report["summary"]
        cols = st.columns(3)
        for col, label, value, note in (
            (cols[0], "Workouts recorded", overview["workout_pct"], f'{summary["linked_workouts"]} of {summary["due_workouts"]} planned workouts linked'),
            (cols[1], "Planned sets logged", overview["set_pct"], f'{summary["covered_sets"]} of {summary["planned_sets"]} sets'),
            (cols[2], "Sets within range", overview["range_pct"], f'{overview["in_range"]} of {overview["recorded_sets"]} logged sets'),
        ):
            col.metric(label, f"{value:.0f}%" if value is not None else "—")
            col.caption(note)
        if not summary["due_workouts"]:
            st.info("No elapsed planned days in this period. Today and future dates are excluded.")
        else:
            gap = overview["largest_gap"]
            message = f"Largest gap: {gap[0]} — {gap[1]} planned sets without a matching log." if gap else "All planned sets are covered by linked logs in this period."
            st.markdown(f'<div class="analysis-insight">{escape(message)}</div>', unsafe_allow_html=True)
            chart_label("Weekly execution")
            st.plotly_chart(weekly_execution_chart(overview["weeks"]), width="stretch", key="weekly_plan_execution")
        st.caption("Completed calendar days only. An unlinked workout is not proof that it was skipped.")
        if any(row["training_phase"] == "deload" for row in performance):
            st.caption("Deload dates use reduced set/repetition targets for resistance exercises. Deload logs are excluded from exercise progress comparisons.")
        self.render_performance(performance)
        with st.expander("Exercise replacements & data corrections"):
            self._render_matches(data)
        with st.expander("Definitions & source data"):
            st.caption(f'On the planned day: {summary["on_time_workouts"]}/{summary["linked_workouts"]} linked workouts. RIR missing: {overview["missing_rir"]}/{overview["recorded_sets"]} logged sets.')
            st.caption("Coverage uses inferred or explicitly marked working sets, plus unknown-effort and timed logs; deload uses its own targets. Light/low-effort work stays in history. Missing RIR is not zero. These indicators do not measure technique or muscle growth.")
            if report["workouts"]:
                st.dataframe(pd.DataFrame([{"Planned date": row["scheduled_date"], "Workout": row["name"], "Recorded date": row["performed_on"], "Status": row["status"], "Sets logged": row["covered_sets"], "Sets planned": row["planned_sets"]} for row in report["workouts"]]), hide_index=True, width="stretch")

    @staticmethod
    def _set_label(item, unit):
        quantity = f'{item["seconds"]}s' if unit == "seconds" else f'{item["reps"]} reps'
        load = f' @ {item["weight"]:g} kg' if item["weight"] else ""
        return f'{quantity}{load} · RIR {item["rir"] if item["rir"] is not None else "?"}'

    def render_performance(self, rows):
        section_header("Exercise trends")
        observed = [row for row in rows if row["sets"]]
        if not observed:
            st.caption("No matching logs in this period. Link a session or confirm a replacement to see its trend.")
            return
        contexts = list(dict.fromkeys(row["context"] for row in observed))
        selected = st.selectbox("Explore an exercise", contexts, key="performance_context", format_func=lambda key: f'{key[0]} · {self._name(key[5])} · {key[7]} × {key[8]}–{key[9]} {key[6]} · position {key[3]}')
        selected_rows = [row for row in observed if row["context"] == selected]
        latest = selected_rows[-1]
        st.markdown(f'<div class="analysis-insight">{escape(latest["comparison"])}</div>', unsafe_allow_html=True)
        st.caption(f'Last recorded {latest["performed_on"]:%d %b %Y} · {latest["in_range"]}/{latest["planned_sets"]} sets in range · {latest["rir_status"]}')
        fig = exercise_history_chart(selected_rows)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="plan_exercise_history")
        st.caption("Shaded band = target range at each date; amber diamonds = deload. Means describe logged sets, including partial sessions. Read load alongside reps/time; substitutes keep separate histories.")
        with st.expander("Previous vs current · set breakdown"):
            previous = latest["previous"]
            if previous:
                st.caption(f'Previous: {previous["performed_on"]:%d %b %Y} · Current: {latest["performed_on"]:%d %b %Y}. History may extend outside the selected month.')
            else:
                st.caption("No prior execution with the same workout context and targets.")
            old_sets = previous["sets"] if previous else ()
            st.dataframe(pd.DataFrame([{"Set": index + 1, "Previous": self._set_label(old_sets[index], latest["unit"]) if index < len(old_sets) else "—", "Current": self._set_label(latest["sets"][index], latest["unit"]) if index < len(latest["sets"]) else "—"} for index in range(latest["planned_sets"])]), hide_index=True, width="stretch")
            st.caption("Changed loads and incomplete counts are not automatically graded. Missing RIR stays unknown. Context or target changes start a new history.")

    def _render_matches(self, data):
        linked = [item for item in data.workouts if item.slot.session_id is not None]
        if not linked:
            st.caption("Link a session in the calendar before confirming a replacement.")
            return
        index = st.selectbox("Linked workout", range(len(linked)), key="match_workout", format_func=lambda value: f'{linked[value].slot.scheduled_date:%d %b %Y} · {linked[value].slot.name}')
        workout, slot = linked[index], linked[index].slot
        index = st.selectbox("Planned exercise", range(len(workout.targets)), key=f"match_target_{slot.session_id}", format_func=lambda value: f'{value + 1}. {self._name(workout.targets[value].exercise.exercise_id)}')
        target = workout.targets[index]
        confirmations = {item.plan_exercise_id: item.workout_exercise_id for item in data.matches if item.session_id == slot.session_id}
        current = confirmations.get(target.plan_exercise_id)
        reserved = {value for key, value in confirmations.items() if key != target.plan_exercise_id}
        candidates = {item.workout_exercise_id: item for item in data.recorded if item.session_id == slot.session_id and item.workout_exercise_id not in reserved and item.exercise_id != target.exercise.exercise_id and any(compatible_set(recorded, target.exercise.target_unit) for recorded in item.sets)}
        prefix = f"replacement_{slot.session_id}_{target.plan_exercise_id}"
        selected = st.selectbox("Exercise actually performed", [None, *candidates], index=list(candidates).index(current) + 1 if current in candidates else 0, key=f"{prefix}_exercise", format_func=lambda value: "Use the planned exercise" if value is None else f"{self._name(candidates[value].exercise_id)} · entry #{value}")
        left, right = st.columns(2)
        if left.button("Confirm replacement", key=f"{prefix}_confirm", disabled=selected is None):
            self._change(slot.session_id, target.plan_exercise_id, selected)
        if current is not None and right.button("Remove replacement", key=f"{prefix}_remove"):
            self._change(slot.session_id, target.plan_exercise_id, None)
        st.caption("Approval applies to this session only. It changes coverage, not the original plan or recorded exercise.")

    def _change(self, session_id, target_id, actual_id):
        try:
            if actual_id is None:
                self.dm.remove_exercise_match(session_id, target_id)
            else:
                self.dm.save_exercise_match(session_id, target_id, actual_id)
        except ValueError as exc:
            st.error(str(exc))
            return
        except SQLAlchemyError:
            logger.exception("Unable to save exercise replacement")
            st.error("The replacement could not be saved. Please try again.")
            return
        st.rerun()
