"""Assign a specific recorded session from its History header."""

import logging
from datetime import timedelta

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
SESSION_LINK_KEY = "history_link_session"


def _close_link_dialog():
    st.session_state.pop(SESSION_LINK_KEY, None)


@st.dialog("Link session to plan", icon=":material/link:", on_dismiss=_close_link_dialog)
def session_plan_link_dialog(manager, session_id, recorded_date):
    """Keep the session fixed while choosing the plan and its scheduled occurrence."""
    try:
        _render_link_dialog(manager, session_id, recorded_date)
    except ValueError as exc:
        st.error(str(exc))
    except SQLAlchemyError:
        logger.exception("Unable to edit session plan link")
        st.error("The plan link could not be loaded or saved. Please try again.")


def _render_link_dialog(manager, session_id, recorded_date):
    prefix = f"history_link_{session_id}"
    st.caption(f"Session #{session_id} · Recorded on {recorded_date:%d %b %Y}")
    current = manager.load_session_plan_assignments((session_id,)).get(session_id)
    plans = manager.load_training_plan_names()
    if current:
        st.info(
            f"Linked to {current['plan_name']} · {current['day_name']} · "
            f"{current['scheduled_date']:%d %b %Y}"
        )
        if st.button("Remove link", key=f"{prefix}_unlink", icon=":material/link_off:"):
            manager.unassign_scheduled_session(
                current["day_id"], current["scheduled_date"], session_id
            )
            st.session_state["history_workout_notice"] = "Plan link removed."
            _close_link_dialog()
            st.rerun()
        st.caption(
            "Removing the link preserves the historical prescription and training phase. "
            "Relinking replaces that context and clears live replacement matches."
        )
    else:
        retained = manager.load_retained_session_context(session_id)
        if retained:
            phase = {"normal": "ordinary", "deload": "deload", "unknown": "unknown"}[
                retained["phase"]
            ]
            st.info(f"Retained training context · {retained['workout']} · phase: {phase}")
            with st.popover("Correct retained context"):
                st.caption(
                    "Relink to the correct workout if known. Clear the retained context when the old assignment was wrong and the correct context is unknown."
                )
                confirmed = st.checkbox(
                    "The retained context is incorrect", key=f"{prefix}_confirm_clear"
                )
                if st.button(
                    "Clear retained context", key=f"{prefix}_clear", disabled=not confirmed
                ):
                    manager.clear_retained_session_context(session_id)
                    st.session_state["history_workout_notice"] = (
                        "Retained training context cleared."
                    )
                    _close_link_dialog()
                    st.rerun()
    if not plans:
        st.info("Create a training plan in Plan before linking this session.")
        return

    default_plan = current["plan_id"] if current else st.session_state.get("active_plan_id")
    plan_key = f"{prefix}_plan"
    if st.session_state.get(plan_key) not in plans:
        st.session_state[plan_key] = default_plan if default_plan in plans else next(iter(plans))
    plan_id = st.selectbox(
        "Training plan", list(plans), key=plan_key, format_func=plans.__getitem__
    )
    anchor = current["scheduled_date"] if current else recorded_date
    chosen_week = st.date_input(
        "Planned week",
        value=anchor,
        key=f"{prefix}_week",
        help="Choose any date in the week this workout was planned for.",
    )
    start = chosen_week - timedelta(days=chosen_week.weekday())
    end = start + timedelta(days=6)
    slots = manager.load_scheduled_workouts(plan_id, start, end)
    available = {
        (slot.day_id, slot.scheduled_date): slot
        for slot in slots
        if slot.session_id in (None, session_id)
    }
    st.caption(f"Planned workouts · {start:%d %b %Y} – {end:%d %b %Y}")
    if not available:
        st.info("No available workouts in this week. Choose another week or plan.")
        return
    slot_key = f"{prefix}_slot"
    if st.session_state.get(slot_key) not in available:
        preferred = (current["day_id"], current["scheduled_date"]) if current else None
        st.session_state[slot_key] = (
            preferred
            if preferred in available
            else min(available, key=lambda key: abs((key[1] - recorded_date).days))
        )
    selected = st.selectbox(
        "Planned workout",
        list(available),
        key=slot_key,
        format_func=lambda key: f"{key[1]:%a, %d %b} · {available[key].name}",
    )
    if selected[1] != recorded_date:
        st.caption(
            "The recorded date stays unchanged; this workout was performed on a different day."
        )
    if st.button(
        "Save link" if current else "Link session",
        key=f"{prefix}_save",
        type="primary",
        icon=":material/link:",
    ):
        manager.assign_scheduled_session(
            selected[0], selected[1], session_id, replace_existing=True
        )
        st.session_state["history_workout_notice"] = (
            f"Session linked to {available[selected].name}."
        )
        _close_link_dialog()
        st.rerun()
