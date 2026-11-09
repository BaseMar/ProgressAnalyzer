"""Convert storage rows into domain models; no database access or caching."""

import pandas as pd

from models import (
    BodyComposition,
    BodyMeasurement,
    Exercise,
    ExerciseMuscleTarget,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)
from models.plan_adherence import RecordedExercise
from models.set_load import SetLoad

MEASUREMENT_COLUMNS = ("chest", "waist", "abdomen", "hips", "thigh", "calf", "biceps")


def map_workout_session(row: dict) -> WorkoutSession:
    return WorkoutSession(
        session_id=row["session_id"],
        session_date=row["session_date"],
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
    )


def map_workout_exercise(row: dict) -> WorkoutExercise:
    return WorkoutExercise(
        workout_exercise_id=row["workout_exercise_id"],
        session_id=row["session_id"],
        exercise_id=row["exercise_id"],
    )


def map_workout_set(row: dict) -> WorkoutSet:
    load = None
    if not pd.isna(row.get("load_type")):
        load = SetLoad(
            load_type=row["load_type"],
            external_weight_kg=float(row["weight"]),
            body_mass_kg=None if pd.isna(row.get("body_mass_kg")) else float(row["body_mass_kg"]),
            assistance_kg=None
            if pd.isna(row.get("assistance_kg"))
            else float(row["assistance_kg"]),
        )
    return WorkoutSet(
        workout_exercise_id=row["workout_exercise_id"],
        set_number=row["set_number"],
        repetitions=row["repetitions"],
        weight=row["weight"],
        rir=None if pd.isna(row.get("rir")) else int(row["rir"]),
        duration_seconds=row.get("duration_seconds"),
        is_warmup=None if pd.isna(row.get("is_warmup")) else bool(row["is_warmup"]),
        load=load,
    )


def map_exercise(row: dict) -> Exercise:
    return Exercise(
        exercise_id=row["exercise_id"],
        name=row["exercise_name"],
        primary_muscle_group_id=None,
        body_part=row.get("body_part"),
    )


def map_recorded_exercises(exercise_rows, set_rows) -> tuple[RecordedExercise, ...]:
    """Group already ordered set rows while preserving recorded entry identity."""
    sets = {row["workout_exercise_id"]: [] for row in exercise_rows}
    for row in set_rows:
        sets[row["workout_exercise_id"]].append(
            map_workout_set(
                {
                    **row,
                    "repetitions": row["repetitions"] or 0,
                    "weight": row["weight"] or 0.0,
                }
            )
        )
    return tuple(
        RecordedExercise(
            row["workout_exercise_id"],
            row["session_id"],
            row["exercise_id"],
            tuple(sets[row["workout_exercise_id"]]),
        )
        for row in exercise_rows
    )


def map_exercise_muscle_target(row: dict) -> ExerciseMuscleTarget:
    return ExerciseMuscleTarget(
        exercise_id=row["exercise_id"],
        muscle_group=row["muscle_group"],
        muscle_name=row["muscle_name"],
        role=row["role"],
        set_factor=float(row["set_factor"]),
    )


def map_body_measurement(row: dict) -> list[BodyMeasurement]:
    """Map one DB row with multiple columns to a list of BodyMeasurement instances."""
    measurements = []
    date = row["measurement_date"]

    for col in MEASUREMENT_COLUMNS:
        value = row.get(col)
        if value is not None:
            measurements.append(
                BodyMeasurement(
                    date=date,
                    measurement_type=col,
                    value=value,
                )
            )
    return measurements


def map_body_composition(row: dict) -> BodyComposition:
    return BodyComposition(
        date=row["measurement_date"],
        weight=row["weight"],
        muscle_mass=row["muscle_mass"],
        fat_mass=row["fat_mass"],
        water_mass=row["water_mass"],
        fat_percentage=row["body_fat_percentage"],
        method=row["method"],
    )
