"""Session-specific replacement approval, owned by History."""

import logging

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from metrics.plan_adherence import compatible_set

logger = logging.getLogger(__name__)


class ExerciseReplacementsView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.names = exercise_names or {}

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self, data):
        linked = [item for item in data.workouts if item.slot.session_id is not None]
        if not linked:
            st.caption("Link a session in the calendar before confirming a replacement.")
            return
        index = st.selectbox(
            "Linked workout",
            range(len(linked)),
            key="match_workout",
            format_func=lambda value: (
                f"{linked[value].slot.scheduled_date:%d %b %Y} · {linked[value].slot.name}"
            ),
        )
        workout, slot = linked[index], linked[index].slot
        index = st.selectbox(
            "Planned exercise",
            range(len(workout.targets)),
            key=f"match_target_{slot.session_id}",
            format_func=lambda value: (
                f"{value + 1}. {self._name(workout.targets[value].exercise.exercise_id)}"
            ),
        )
        target = workout.targets[index]
        confirmations = {
            item.plan_exercise_id: item.workout_exercise_id
            for item in data.matches
            if item.session_id == slot.session_id
        }
        current = confirmations.get(target.plan_exercise_id)
        reserved = {value for key, value in confirmations.items() if key != target.plan_exercise_id}
        candidates = {
            item.workout_exercise_id: item
            for item in data.recorded
            if item.session_id == slot.session_id
            and item.workout_exercise_id not in reserved
            and item.exercise_id != target.exercise.exercise_id
            and any(compatible_set(recorded, target.exercise.target_unit) for recorded in item.sets)
        }
        prefix = f"replacement_{slot.session_id}_{target.plan_exercise_id}"
        selected = st.selectbox(
            "Exercise actually performed",
            [None, *candidates],
            index=list(candidates).index(current) + 1 if current in candidates else 0,
            key=f"{prefix}_exercise",
            format_func=lambda value: (
                "Use the planned exercise"
                if value is None
                else f"{self._name(candidates[value].exercise_id)} · entry #{value}"
            ),
        )
        left, right = st.columns(2)
        if left.button("Confirm replacement", key=f"{prefix}_confirm", disabled=selected is None):
            self._change(slot.session_id, target.plan_exercise_id, selected)
        if current is not None and right.button("Remove replacement", key=f"{prefix}_remove"):
            self._change(slot.session_id, target.plan_exercise_id, None)
        st.caption(
            "Approval applies to this session only. It changes coverage, not the original plan or recorded exercise."
        )

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
