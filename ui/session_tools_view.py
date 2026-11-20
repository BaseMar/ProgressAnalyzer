"""Session corrections in a dialog, leaving the workout list uncluttered."""

import logging
from dataclasses import replace

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.exercise_replacements_view import ExerciseReplacementsView
from ui.session_plan_link_view import SESSION_LINK_KEY
from ui.set_classification_view import render_set_classification
from ui.set_load_view import render_set_load_correction

logger = logging.getLogger(__name__)
SESSION_TOOLS_KEY = "history_tools_session"


def _close_tools_dialog():
    st.session_state.pop(SESSION_TOOLS_KEY, None)


@st.dialog("Session tools", width="large", icon=":material/tune:", on_dismiss=_close_tools_dialog)
def session_tools_dialog(manager, session_id, recorded_date, exercise_names=None):
    st.caption(f"Session #{session_id} · Recorded on {recorded_date:%d %b %Y}")
    labels, loads, replacements, deletion = st.tabs(
        ["Set labels", "Set load", "Replacements", "Delete session"],
        key=f"history_tools_tab_{session_id}",
        on_change="rerun",
    )
    if labels.open:
        with labels:
            render_set_classification(
                manager, session_id=session_id, embedded=True, show_toggle=False
            )
    if loads.open:
        with loads:
            render_set_load_correction(
                manager,
                session_id=session_id,
                workout_date=recorded_date,
                embedded=True,
                show_toggle=False,
            )
    if replacements.open:
        with replacements:
            _render_replacements(manager, session_id, recorded_date, exercise_names)
    if deletion.open:
        with deletion:
            st.warning("Deleting this session permanently removes its recorded exercises and sets.")
            with st.container(key=f"history_delete_{session_id}"):
                if st.button("Delete Session", key=f"del_{session_id}", icon=":material/delete:"):
                    if manager.delete_session(session_id):
                        _close_tools_dialog()
                        st.session_state["history_workout_notice"] = "Session deleted."
                        st.rerun()
                    st.error("The session could not be deleted. Please try again.")


def _render_replacements(manager, session_id, recorded_date, exercise_names):
    try:
        current = (
            manager.load_session_plan_assignments((session_id,)).get(session_id)
            if manager.plan_schedule_storage_ready()
            else None
        )
        if current is None:
            st.info("Link this session to a plan before confirming an exercise replacement.")
            if st.button(
                "Link to plan", key=f"history_tools_link_{session_id}", icon=":material/link:"
            ):
                _close_tools_dialog()
                st.session_state[SESSION_LINK_KEY] = (session_id, recorded_date)
                st.rerun()
            return
        data = manager.load_plan_adherence(
            current["plan_id"], current["scheduled_date"], current["scheduled_date"]
        )
        data = replace(
            data,
            workouts=tuple(
                workout for workout in data.workouts if workout.slot.session_id == session_id
            ),
        )
        ExerciseReplacementsView(manager, exercise_names).render(
            data, workout_key=f"match_workout_session_{session_id}"
        )
    except SQLAlchemyError:
        logger.exception("Unable to load session replacements")
        st.error("Replacement data could not be loaded. Please try again.")
