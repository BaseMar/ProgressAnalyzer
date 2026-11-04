"""Plan overlays and explicit session assignment controls for the calendar."""

from datetime import date
from html import escape
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.utils.ui_helpers import section_header

logger = logging.getLogger(__name__)


class PlanScheduleView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.exercise_names = exercise_names or {}
        self.plan_id = None
        self.version_dates = []

    def render_picker(self):
        try:
            if not self.dm.plan_schedule_storage_ready():
                return
            by_id = {plan.plan_id: plan for plan in self.dm.load_training_plans()}
            if not by_id:
                return
            self.plan_id = st.selectbox(
                "Calendar plan", [None, *by_id], index=1, key="calendar_plan",
                format_func=lambda value: "Workout history only" if value is None else by_id[value].draft.name,
            )
            if self.plan_id is not None:
                self.version_dates = [version.draft.effective_from for version in self.dm.load_training_plan_versions(self.plan_id)]
        except SQLAlchemyError:
            logger.exception("Unable to load calendar plans")
            st.warning("Planned workouts could not be loaded. Workout history is still available.")
            self.plan_id = None

    def load_month(self, start, end):
        if self.plan_id is None:
            return []
        try:
            return self.dm.load_scheduled_workouts(self.plan_id, start, end)
        except SQLAlchemyError:
            logger.exception("Unable to load planned workouts")
            st.warning("Planned workouts could not be loaded. Please try again.")
            return []

    def render_day(self, day, slots):
        if self.plan_id is None:
            return
        section_header("Planned Workouts")
        day_slots = [slot for slot in slots if slot.scheduled_date == day]
        if not day_slots:
            st.caption("No planned workouts for this day.")
            return
        try:
            assigned = self.dm.load_plan_session_links()
            session_frame = self.dm.load_sessions()
            available = session_frame.loc[~session_frame["session_id"].isin(assigned)].sort_values(
                ["session_date", "session_id"], ascending=False,
            )
            for slot in day_slots:
                self._render_slot(slot, available)
        except SQLAlchemyError:
            logger.exception("Unable to load planned workout details")
            st.error("Planned workout details could not be loaded. Please try again.")

    def _render_slot(self, slot, available):
        prefix = f"schedule_{slot.day_id}_{slot.scheduled_date.isoformat()}"
        with st.container(key=f"planned_workout_{slot.day_id}"):
            st.markdown(f'<div class="plan-workout-heading">{escape(slot.name)}</div>', unsafe_allow_html=True)
            st.caption(f"Planned for {slot.scheduled_date:%A, %d %B}")
            if slot.session_id is not None:
                moved = " · Performed on a different day" if slot.performed_on != slot.scheduled_date else ""
                st.success(f"Linked to session #{slot.session_id} · {slot.performed_on:%d %b %Y}{moved}")
                if st.button("Remove link", key=f"{prefix}_unlink"):
                    self._save_link(slot, unlink=True)
            else:
                if available.empty:
                    st.caption("No unlinked sessions available. Import a workout log first.")
                    return
                dates = sorted(set(pd.to_datetime(available["session_date"]).dt.date), reverse=True)
                default = min(dates, key=lambda value: abs((value - slot.scheduled_date).days))
                left, right = st.columns(2)
                recorded_date = left.selectbox("1 · Recorded on", dates, index=dates.index(default),
                                               key=f"{prefix}_date", format_func=lambda value: value.strftime("%a, %d %b %Y"),
                                               on_change=st.session_state.__setitem__, args=(f"{prefix}_session", None))
                candidates = available.loc[pd.to_datetime(available["session_date"]).dt.date == recorded_date]
                labels = {}
                for index, row in enumerate(candidates.itertuples(), start=1):
                    start = getattr(row, "start_time", None)
                    labels[int(row.session_id)] = f"Session {index}" + (f" · {start:%H:%M}" if hasattr(start, "strftime") else "")
                session_id = right.selectbox("2 · Recorded session", [None, *labels], key=f"{prefix}_session",
                                              format_func=lambda value: "Choose a session" if value is None else labels[value])
                if st.button("Link session", key=f"{prefix}_link", disabled=session_id is None, type="primary"):
                    self._save_link(slot, session_id=session_id)
                st.caption("Choose another date above if this workout was moved.")

    def _save_link(self, slot, *, session_id=None, unlink=False):
        try:
            if unlink:
                self.dm.unassign_scheduled_session(slot.day_id, slot.scheduled_date, slot.session_id)
            else:
                self.dm.assign_scheduled_session(slot.day_id, slot.scheduled_date, session_id)
        except ValueError as exc:
            st.error(str(exc))
            return
        except SQLAlchemyError:
            logger.exception("Unable to update planned workout link")
            st.error("The link could not be saved. Please try again.")
            return
        st.rerun()
