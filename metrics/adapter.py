import pandas as pd

from metrics.input import MetricsInput
from models import (WorkoutSession, WorkoutExercise, WorkoutSet, Exercise, BodyMeasurement, BodyComposition,)


def build_metrics_input(df_sessions: pd.DataFrame, df_sets: pd.DataFrame, df_exercises: pd.DataFrame,              df_body_measurements: pd.DataFrame | None = None, df_body_composition: pd.DataFrame | None = None, ) -> MetricsInput:
    """
    Build MetricsInput from raw database DataFrames.

    This is the ONLY place where:
    - pandas is used
    - DB column names are mapped to domain models
    """

    # ---- sessions ----
    sessions = [
        WorkoutSession(session_id=row.SessionID, session_date=row.SessionDate, start_time=None, end_time=None,)
        for row in df_sessions.itertuples()]

    # ---- exercises ----
    exercises = [
        Exercise(exercise_id=row.ExerciseID, name=row.ExerciseName, primary_muscle_group_id=None,)
        for row in df_exercises.itertuples()]

    # ---- workout_exercises ----
    workout_exercises = []
    we_map = {}

    for row in df_sets.itertuples():
        key = (row.SessionDate, row.ExerciseName)
        if key not in we_map:
            we_id = len(we_map) + 1
            we_map[key] = we_id
            workout_exercises.append(WorkoutExercise(workout_exercise_id=we_id, session_id=None, exercise_id=None,))

    # ---- sets ----
    sets = [
        WorkoutSet(workout_exercise_id=we_map[(row.SessionDate, row.ExerciseName)], set_number=row.SetNumber,repetitions=row.Repetitions, weight=row.Weight, rir=row.RIR,)
        for row in df_sets.itertuples()]

    # ---- body measurements ----
    body_measurements = []
    if df_body_measurements is not None:
        for row in df_body_measurements.itertuples():
            for field in ["Chest", "Waist", "Abdomen", "Hips", "Thigh", "Calf", "Biceps"]:
                value = getattr(row, field)
                if value is not None:
                    body_measurements.append(BodyMeasurement(date=row.MeasurementDate, measurement_type=field.lower(), value=value,))

    # ---- body composition ----
    body_composition = []
    if df_body_composition is not None:
        body_composition = [BodyComposition( date=row.MeasurementDate, weight=row.Weight, fat_percentage=row.BodyFatPercentage, muscle_mass=row.MuscleMass,)
            for row in df_body_composition.itertuples()]

    return MetricsInput(
        sessions=sessions,
        workout_exercises=workout_exercises,
        sets=sets,
        exercises=exercises,
        muscle_groups=[],
        body_measurements=body_measurements,
        body_composition=body_composition,
    )
