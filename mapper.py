from models import (
    BodyComposition,
    BodyMeasurement,
    Exercise,
    ExerciseMuscleTarget,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

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
    return WorkoutSet(
        workout_exercise_id=row["workout_exercise_id"],
        set_number=row["set_number"],
        repetitions=row["repetitions"],
        weight=row["weight"],
        rir=row.get("rir"),
    )


def map_exercise(row: dict) -> Exercise:
    return Exercise(
        exercise_id=row["exercise_id"],
        name=row["exercise_name"],
        primary_muscle_group_id=None,
        body_part=row.get("body_part"),
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
