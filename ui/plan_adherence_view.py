"""Plan execution summary and explicit, session-scoped exercise replacements."""

from datetime import date, timedelta
from calendar import monthrange
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from metrics.plan_adherence import compatible_set, compute_plan_adherence
from ui.utils.ui_helpers import section_header

logger = logging.getLogger(__name__)


class PlanAdherenceView:
    def __init__(self, *, manager=None, exercise_names=None, selected_month=None):
        self.dm = manager if manager is not None else DataManager()
        self.names = exercise_names or {}
        self.selected_month = selected_month

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self):
        section_header("Plan Execution")
        try:
            if not self.dm.adherence_storage_ready():
                st.info("Plan execution analysis is not available until database setup is complete.")
                return
            plans = {item.plan_id: item for item in self.dm.load_training_plans()}
            if not plans:
                st.info("Create a Training Plan and link recorded sessions in the dashboard calendar to track its execution.")
                return
            plan_id = st.selectbox("Analysis plan", list(plans), key="adherence_plan",
                                   format_func=lambda value: plans[value].draft.name)
            versions = self.dm.load_training_plan_versions(plan_id)
            if self.selected_month not in (None, "All time"):
                start = date.fromisoformat(f"{self.selected_month}-01")
                end = start.replace(day=monthrange(start.year, start.month)[1])
            else:
                start = min(item.draft.effective_from for item in versions)
                end = max(date.today(), start) + timedelta(days=7)
            data = self.dm.load_plan_adherence(plan_id, start, end)
        except SQLAlchemyError:
            logger.exception("Unable to load adherence analysis")
            st.error("Plan execution analysis could not be loaded. Please try again.")
            return
        report = compute_plan_adherence(data, as_of=date.today())
        summary = report["summary"]
        st.caption("Summary includes scheduled dates before today. Today and future dates do not lower your results. Sessions moved to another day still count as recorded.")
        columns = st.columns(5)
        for col, label, covered, total in (
            (columns[0], "Workouts recorded", summary["linked_workouts"], summary["due_workouts"]),
            (columns[1], "Fully completed", summary["complete_workouts"], summary["due_workouts"]),
            (columns[2], "On planned day", summary["on_time_workouts"], summary["linked_workouts"]),
            (columns[3], "Exercises covered", summary["covered_exercises"], summary["planned_exercises"]),
            (columns[4], "Sets covered", summary["covered_sets"], summary["planned_sets"]),
        ):
            col.metric(label, f"{covered} / {total}" if total else "—")
        st.caption("Coverage counts logged sets, capped at the plan target. A completed workout meets its planned set counts; this does not assess technique, RIR, target-range success or muscle growth. Unmarked warm-up sets are included.")
        if report["workouts"]:
            st.dataframe(pd.DataFrame([{
                "Planned date": row["scheduled_date"], "Workout": row["name"],
                "Recorded date": row["performed_on"], "Status": row["status"],
                "Exercises": f'{row["covered_exercises"]}/{row["planned_exercises"]}',
                "Sets": f'{row["covered_sets"]}/{row["planned_sets"]}',
                "Included in summary": row["eligible"],
            } for row in report["workouts"]]), hide_index=True, width="stretch")
        else:
            st.info("No workouts are scheduled in this period.")

    def render_workout(self, slot, plan_id):
        try:
            if not self.dm.adherence_storage_ready():
                return
            data = self.dm.load_plan_adherence(plan_id, slot.scheduled_date, slot.scheduled_date)
            workout = next(item for item in data.workouts if item.slot.day_id == slot.day_id)
            row = next(item for item in compute_plan_adherence(data, as_of=date.today())["workouts"]
                       if item["day_id"] == slot.day_id)
            st.markdown(f'**Plan coverage: {row["covered_sets"]}/{row["planned_sets"]} sets · {row["status"]}**')
            st.dataframe(pd.DataFrame([{
                "Planned exercise": self._name(item["exercise_id"]),
                "Approved replacement": self._name(item["replacement_exercise_id"]) if item["replacement_exercise_id"] else "—",
                "Recorded sets": item["covered_sets"], "Planned sets": item["planned_sets"],
            } for item in row["details"]]), hide_index=True, width="stretch")
            with st.expander("Confirm exercise replacements"):
                st.caption("Approve a replacement from this session only. It counts toward plan coverage; its strength history remains separate. One recorded exercise cannot cover multiple planned positions.")
                confirmations = {item.plan_exercise_id: item.workout_exercise_id for item in data.matches if item.session_id == slot.session_id}
                for index, target in enumerate(workout.targets, start=1):
                    current = confirmations.get(target.plan_exercise_id)
                    reserved = {value for key, value in confirmations.items() if key != target.plan_exercise_id}
                    candidates = {item.workout_exercise_id: item for item in data.recorded
                                  if item.session_id == slot.session_id and item.workout_exercise_id not in reserved
                                  and item.exercise_id != target.exercise.exercise_id
                                  and any(compatible_set(recorded_set, target.exercise.target_unit) for recorded_set in item.sets)}
                    prefix = f"replacement_{slot.session_id}_{target.plan_exercise_id}"
                    selected = st.selectbox(
                        f"Instead of {self._name(target.exercise.exercise_id)} · position {index}",
                        [None, *candidates], index=list(candidates).index(current) + 1 if current in candidates else 0,
                        key=f"{prefix}_exercise",
                        format_func=lambda value: "Use the planned exercise" if value is None else f"{self._name(candidates[value].exercise_id)} · entry #{value}",
                    )
                    left, right = st.columns(2)
                    if left.button("Confirm replacement", key=f"{prefix}_confirm", disabled=selected is None):
                        self._change(slot.session_id, target.plan_exercise_id, selected)
                    if current is not None and right.button("Remove replacement", key=f"{prefix}_remove"):
                        self._change(slot.session_id, target.plan_exercise_id, None)
        except SQLAlchemyError:
            logger.exception("Unable to load workout coverage")
            st.error("Workout coverage could not be loaded. Please try again.")

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
