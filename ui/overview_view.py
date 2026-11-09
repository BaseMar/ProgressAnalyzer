"""Current-plan conclusion, attention on the left, next workout on the right."""

import logging
from datetime import date, timedelta
from html import escape

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from metrics.overview_summary import overview_conclusion
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
        current = max(
            (version for version in versions if version.draft.effective_from <= as_of),
            key=lambda version: version.draft.effective_from,
            default=min(versions, key=lambda version: version.draft.effective_from),
        )
        st.caption(
            f"Current plan · recent 28 days ({start:%d %b}–{as_of:%d %b %Y}) · historical periods are selected in Analysis."
        )
        headline = st.empty()
        with st.container(key="overview_decisions"):
            attention, next_workout = st.columns([1, 1], gap="large")
            # The placeholder above stays first in the page; prepare targets once
            # so the conclusion and annotations use the user's actual preview.
            with next_workout:
                preview = NextWorkoutView(self.dm, self.names).render(
                    plan_id, versions, context=context, history=history, as_of=as_of, compact=True
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
            with attention:
                render_training_insights(report, self.names, show_target_actions=False)
        conclusion = overview_conclusion(report, preview, as_of=as_of, version=current)
        headline.markdown(
            f'<div class="overview-conclusion overview-conclusion--{escape(conclusion.kind)}">'
            '<span class="overview-eyebrow">Your training today</span>'
            f"<h2>{escape(conclusion.title)}</h2><p>{escape(conclusion.detail)}</p></div>",
            unsafe_allow_html=True,
        )
        return plan_id, versions
