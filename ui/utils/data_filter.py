from typing import Tuple

import pandas as pd

from metrics.input import MetricsInput
from metrics.body_metrics import to_date


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
    def in_month(value):
        day = to_date(value)
        return day.year == year and day.month == month_num

    filtered_sessions = [
        session
        for session in input_data.sessions
        if in_month(session.session_date)
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
        body_measurements=[item for item in input_data.body_measurements if in_month(item.date)],
        body_composition=[item for item in input_data.body_composition if in_month(item.date)],
        deload_exercise_ids=input_data.deload_exercise_ids.intersection(workout_exercise_ids),
    )

    filtered_sets_df = sets_df.copy()
    if filtered_sets_df.empty:
        return filtered_input, filtered_sets_df
    filtered_sets_df["session_date"] = pd.to_datetime(filtered_sets_df["session_date"])

    filtered_sets_df = filtered_sets_df[
        (filtered_sets_df["session_date"].dt.year == year)
        & (filtered_sets_df["session_date"].dt.month == month_num)
    ]

    return filtered_input, filtered_sets_df.reset_index(drop=True)
