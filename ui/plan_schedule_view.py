"""Plan overlays and explicit session assignment controls for the calendar."""

from datetime import date
from html import escape
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.utils.ui_helpers import section_header
from ui.plan_adherence_view import PlanAdherenceView

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
            labels = {int(row.session_id): f"{pd.Timestamp(row.session_date):%d %b %Y} · Session #{row.session_id}"
                      for row in available.itertuples()}
            for slot in day_slots:
                self._render_slot(slot, labels)
        except SQLAlchemyError:
            logger.exception("Unable to load planned workout details")
            st.error("Planned workout details could not be loaded. Please try again.")

    def _render_slot(self, slot, session_labels):
        prefix = f"schedule_{slot.day_id}_{slot.scheduled_date.isoformat()}"
        with st.container(key=f"planned_workout_{slot.day_id}"):
            st.markdown(f'<div class="plan-workout-heading">{escape(slot.name)}</div>', unsafe_allow_html=True)
            target = self.dm.load_scheduled_workout_targets(slot.day_id)
            st.dataframe(pd.DataFrame([{
                "Exercise": self.exercise_names.get(item.exercise_id, f"Exercise #{item.exercise_id}"),
                "Sets": item.set_count,
                "Target": f"{item.target_min}–{item.target_max} {item.target_unit}",
                "Target RIR": item.target_rir,
            } for item in target.exercises]), hide_index=True, width="stretch")
            if slot.session_id is not None:
                moved = " · Performed on a different day" if slot.performed_on != slot.scheduled_date else ""
                st.success(f"Linked to session #{slot.session_id} · {slot.performed_on:%d %b %Y}{moved}")
                PlanAdherenceView(manager=self.dm, exercise_names=self.exercise_names).render_workout(slot, self.plan_id)
                if st.button("Remove link", key=f"{prefix}_unlink"):
                    self._save_link(slot, unlink=True)
            else:
                st.caption("Choose a recorded session from any date, including a workout moved to another day.")
                session_id = st.selectbox(
                    "Recorded session", [None, *session_labels], key=f"{prefix}_session",
                    format_func=lambda value: "Choose a session" if value is None else session_labels[value],
                )
                if st.button("Link session", key=f"{prefix}_link", disabled=session_id is None):
                    self._save_link(slot, session_id=session_id)
            st.caption("A link identifies the planned workout; it does not confirm completion of every planned set.")

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
