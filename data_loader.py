from core.data_manager import DataManager
from core.mapper import *
import streamlit as st

from metrics.input import MetricsInput
from metrics.metrics_engine import compute_all_metrics


@st.cache_data
def load_data():
    dm = DataManager()
    sets_df = dm.load_sets_ui()

    sessions = [map_workout_session(row) for row in dm.load_sessions().to_dict("records")]
    workout_exercises = [map_workout_exercise(row) for row in dm.load_workout_exercises().to_dict("records")]
    sets = [map_workout_set(row) for row in dm.load_sets_raw().to_dict("records")]
    exercises = [map_exercise(row) for row in dm.load_exercises().to_dict("records")]
    muscle_groups = list({ex.body_part for ex in exercises if ex.body_part})
    #muscle_groups = [map_muscle_group(row) for row in dm.load_muscle_groups().to_dict("records")]
    body = dm.load_body_data()
    body_measurements = [map_body_measurement(row) for row in body["measurements"].to_dict("records")]
    body_composition = [map_body_composition(row) for row in body["composition"].to_dict("records")]

    metrics_input = MetricsInput(
        sessions=sessions,
        workout_exercises=workout_exercises,
        sets=sets,
        exercises=exercises,
        muscle_groups=muscle_groups,
        body_measurements=body_measurements,
        body_composition=body_composition,
    )

    metrics = compute_all_metrics(metrics_input)

    return metrics, sets_df
