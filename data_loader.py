"""
Data Loader

Responsible for loading and transforming raw data from database into
structured MetricsInput for processing by the metrics engine.

This module bridges the data persistence layer with domain logic.
"""

from typing import Tuple

import pandas as pd
import streamlit as st

from data_manager import DataManager
from mapper import *
from metrics.input import MetricsInput


@st.cache_data
def load_data() -> Tuple[MetricsInput, pd.DataFrame]:
    """Load all application data from database.
    
    This is the main entry point for data loading. Data is cached automatically
    by Streamlit to avoid redundant database queries.
    
    Returns:
        Tuple of:
        - MetricsInput: structured domain objects for metrics computation
        - pd.DataFrame: raw sets data with joined names for UI display
    """
    dm = DataManager()
    sets_df = dm.load_sets_ui()

    sessions = [map_workout_session(row) for row in dm.load_sessions().to_dict("records")]
    workout_exercises = [map_workout_exercise(row) for row in dm.load_workout_exercises().to_dict("records")]
    sets = [map_workout_set(row) for row in dm.load_sets_raw().to_dict("records")]
    exercises = [map_exercise(row) for row in dm.load_exercises().to_dict("records")]
    muscle_groups = list({ex.body_part for ex in exercises if ex.body_part})
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
    
    return metrics_input, sets_df
