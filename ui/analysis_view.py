"""One analytical question at a time; time filters stay on this page."""
from datetime import date
import logging

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.measurement_timeline import measurement_timeline
from metrics.muscle_volume import weekly_plan_sets
from ui.body_metrics_view import BodyMetricsView
from ui.body_parts_view import BodyPartsView
from ui.exercise_view import ExerciseView
from ui.plan_adherence_view import PlanAdherenceView
from ui.utils.data_filter import filter_data_by_month
from ui.utils.active_plan import select_active_plan
from ui.utils.history_period import select_analysis_month
from ui.utils.ui_helpers import page_title

logger = logging.getLogger(__name__)


class AnalysisView:
    def __init__(self, input_data, sets_df, *, manager=None, exercise_names=None):
        self.input = input_data
        self.sets = sets_df
        self.dm = manager
        self.names = exercise_names or {}

    def render(self):
        page_title("Analysis", "Explore your training")
        question, period = st.columns([2, 1])
        with question:
            topic = st.selectbox("What do you want to understand?", ["Exercise progress", "Plan consistency", "Muscle distribution", "Body measurements"], key="analysis_question")
        with period:
            month = select_analysis_month(self.input)
        filtered, sets = filter_data_by_month(self.input, self.sets, month)
        if topic in ("Exercise progress", "Plan consistency"):
            if topic == "Exercise progress":
                scope = st.radio("Compare", ["Plan targets", "All recorded exercises"], horizontal=True, key="analysis_exercise_scope")
                if scope == "All recorded exercises":
                    ExerciseView(compute_exercise_metrics(filtered), sets).render(focused=True)
                    return
            PlanAdherenceView(manager=self.dm, exercise_names=self.names, selected_month=month).render(
                mode="exercise" if topic == "Exercise progress" else "consistency")
        elif topic == "Muscle distribution":
            self._muscle_distribution(filtered, month)
        else:
            BodyMetricsView({"timeline": measurement_timeline(filtered)}, manager=self.dm).render(focused=True)

    def _muscle_distribution(self, filtered, month):
        targets = None
        try:
            manager = self.dm if self.dm is not None else DataManager()
            if manager.training_plan_storage_ready():
                plan_id = select_active_plan(manager.load_training_plans())
                if plan_id is not None:
                    version = manager.load_effective_training_plan(plan_id, date.today())
                    if version is not None:
                        targets, missing = weekly_plan_sets(version.draft, self.input)
                        st.caption(f"Target: {version.draft.name}")
                        if missing:
                            targets = None
                            names = {item.exercise_id: item.name for item in self.input.exercises}
                            st.warning("Targets unavailable: add muscle mappings for " +
                                       ", ".join(names.get(value, f"exercise #{value}") for value in sorted(missing)))
                    else:
                        st.info("This plan has not started yet. Targets will appear on its effective date.")
                else:
                    st.info("Create a plan in Plan to calculate weekly muscle targets automatically.")
            else:
                st.info("Training plan storage needs setup before targets can be calculated.")
        except SQLAlchemyError:
            logger.exception("Unable to load muscle distribution plan")
            st.warning("Plan targets could not be loaded. Recorded sets remain available.")
        BodyPartsView(compute_exercise_metrics(filtered), month, weekly_targets=targets).render()
