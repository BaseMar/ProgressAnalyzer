from typing import Tuple

import pandas as pd

from metrics.input import MetricsInput


def filter_data_by_month(
    input_data: MetricsInput,
    sets_df: pd.DataFrame,
    month: str | None,
) -> Tuple[MetricsInput, pd.DataFrame]:
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
    if month is None or month == "All time":
        return input_data, sets_df

    year, month_num = map(int, month.split("-"))

    filtered_sessions = [
        session
        for session in input_data.sessions
        if session.session_date.year == year and session.session_date.month == month_num
    ]

    session_ids = {s.session_id for s in filtered_sessions}

    filtered_workout_exercises = [
        workout_exercise
        for workout_exercise in input_data.workout_exercises
        if workout_exercise.session_id in session_ids
    ]
    workout_exercise_ids = {we.workout_exercise_id for we in filtered_workout_exercises}

    filtered_sets = [
        workout_set
        for workout_set in input_data.sets
        if workout_set.workout_exercise_id in workout_exercise_ids
    ]

    filtered_input = MetricsInput(
        sessions=filtered_sessions,
        workout_exercises=filtered_workout_exercises,
        sets=filtered_sets,
        exercises=input_data.exercises,
        exercise_muscle_targets=input_data.exercise_muscle_targets,
        muscle_groups=input_data.muscle_groups,
        body_measurements=input_data.body_measurements,
        body_composition=input_data.body_composition,
    )

    filtered_sets_df = sets_df.copy()
    filtered_sets_df["session_date"] = pd.to_datetime(filtered_sets_df["session_date"])

    filtered_sets_df = filtered_sets_df[
        (filtered_sets_df["session_date"].dt.year == year)
        & (filtered_sets_df["session_date"].dt.month == month_num)
    ]

    return filtered_input, filtered_sets_df.reset_index(drop=True)
