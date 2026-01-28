from typing import Tuple
import pandas as pd
from metrics.input import MetricsInput


def filter_data_by_month(input_data: MetricsInput, sets_df: pd.DataFrame, month: str) -> Tuple[MetricsInput, pd.DataFrame]:
    """
    Filter MetricsInput and sets_df to a specific month (YYYY-MM).

    Parameters
    ----------
    input_data : MetricsInput
        Original unfiltered metrics input.
    sets_df : pd.DataFrame
        Raw sets dataframe.
    month : str
        Month in YYYY-MM format.

    Returns
    -------
    Tuple[MetricsInput, pd.DataFrame]
        Filtered MetricsInput and sets_df.
    """
    if not month:
        return input_data, sets_df

    year, month_num = map(int, month.split("-"))

    # ---- Filter sessions ----
    filtered_sessions = [s for s in input_data.sessions if s.session_date.year == year 
                         and s.session_date.month == month_num]

    session_ids = {s.session_id for s in filtered_sessions}

    # ---- Filter workout_exercises ----
    filtered_workout_exercises = [we for we in input_data.workout_exercises if we.session_id in session_ids]
    workout_exercise_ids = {we.workout_exercise_id for we in filtered_workout_exercises}

    # ---- Filter sets ----
    filtered_sets = [s for s in input_data.sets if s.workout_exercise_id in workout_exercise_ids]

    # ---- Rebuild MetricsInput ----
    filtered_input = MetricsInput(
            sessions=filtered_sessions,
            workout_exercises=filtered_workout_exercises,
            sets=filtered_sets,
            exercises=input_data.exercises,
            muscle_groups=input_data.muscle_groups,
            body_measurements=input_data.body_measurements,
            body_composition=input_data.body_composition,
        )

    # ---- Filter sets_df (UI) ----
    sets_df = sets_df.copy()
    sets_df["SessionDate"] = pd.to_datetime(sets_df["SessionDate"])

    filtered_sets_df = sets_df[
        (sets_df["SessionDate"].dt.year == year) &
        (sets_df["SessionDate"].dt.month == month_num)]
 
    return filtered_input, filtered_sets_df
