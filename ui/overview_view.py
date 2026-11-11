"""Progress first, with a separate, visible home for copying the next workout."""

import logging
from datetime import date, timedelta

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from metrics.training_insights import compute_training_insights
from ui.next_workout_view import NextWorkoutView
from ui.training_insights_view import render_training_insights
from ui.utils.active_plan import select_active_plan

logger = logging.getLogger(__name__)


class OverviewView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.names = exercise_names or {}

    def render(self, *, as_of=None):
        as_of = as_of or date.today()
        try:
            if not self.dm.adherence_storage_ready():
                st.info(
                    "Plan analysis needs setup. Your recorded sessions are available in History."
                )
                return None, ()
            plans = self.dm.load_training_plans()
            with st.container(key="overview_plan_filter"):
                plan_id = select_active_plan(plans)
            if plan_id is None:
                st.info(
                    "Start with a Training Plan. Add exercises and training days to receive progression targets."
                )
                return None, ()
            versions = self.dm.load_training_plan_versions(plan_id)
            if not versions:
                st.info("Save a plan version to start the overview.")
                return None, ()
            start = as_of - timedelta(days=27)
            preview_end = max(
                as_of, min(version.draft.effective_from for version in versions)
            ) + timedelta(days=28)
            context = self.dm.prepare_plan_context(
                plan_id, start, preview_end, as_of=as_of, versions=versions
            )
            history = context.history
        except SQLAlchemyError:
            logger.exception("Unable to load current plan overview")
            st.error(
                "The plan overview could not be loaded. Your recorded sessions remain available in History."
            )
            return None, ()
        settings = {version.version_id: version.draft.progression for version in versions}
        with st.container(key="overview_tabs"):
            progress, next_workout = st.tabs(["Progress", "Next workout"])
        summary_area = progress.container(key="overview_progress_summary")
        insights_area = progress.container(key="overview_progress_insights")
        with next_workout:
            preview = NextWorkoutView(self.dm, self.names).render(
                plan_id, versions, context=context, history=history, as_of=as_of
            )
        report = compute_training_insights(
            history,
            as_of=as_of,
            start=start,
            end=as_of,
            settings_by_version=settings,
            preview=preview,
            date_basis="performed",
        )
        with summary_area:
            st.subheader("Your progress")
            st.caption(f"Last 28 days: {start:%d %b} to {as_of:%d %b %Y}")
            counts = report.exercise_progress
            with st.container(key="overview_progress_kpis"):
                improving, unchanged, lower = st.columns(3)
                for column, label, value, explanation in (
                    (
                        improving,
                        "Improving exercises",
                        counts.improving,
                        "More reps or seconds at unchanged per-set loads and, for repetitions, the same recorded RIR.",
                    ),
                    (
                        unchanged,
                        "No clear change",
                        counts.unchanged,
                        "The same total reps or seconds under comparable conditions. This does not diagnose a plateau.",
                    ),
                    (
                        lower,
                        "Lower results",
                        counts.lower,
                        "Fewer reps or seconds under comparable conditions. One result does not establish regression or fatigue.",
                    ),
                ):
                    column.metric(label, value if counts.compared else "\u2014", help=explanation)
            st.caption(
                f"Compared exercises: {counts.compared}. Awaiting comparable data: {counts.unassessed}."
            )
            if not counts.compared:
                st.caption(
                    "A comparison needs two complete results in the same exercise context, with unchanged loads and reserve. Changed loads, incomplete logs and deloads are not graded."
                )
        with insights_area:
            render_training_insights(report, self.names, show_target_actions=False)
        return plan_id, versions
