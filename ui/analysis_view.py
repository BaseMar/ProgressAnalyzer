"""One analytical question at a time; time filters stay on this page."""
import streamlit as st

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.measurement_timeline import measurement_timeline
from ui.body_metrics_view import BodyMetricsView
from ui.body_parts_view import BodyPartsView
from ui.exercise_view import ExerciseView
from ui.plan_adherence_view import PlanAdherenceView
from ui.utils.data_filter import filter_data_by_month
from ui.utils.history_period import select_analysis_month
from ui.utils.ui_helpers import page_title


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
            BodyPartsView(compute_exercise_metrics(filtered), month).render(focused=True)
        else:
            BodyMetricsView({"timeline": measurement_timeline(filtered)}, manager=self.dm).render(focused=True)
