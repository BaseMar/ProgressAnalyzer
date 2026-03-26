from models import (WorkoutSession, WorkoutExercise, WorkoutSet, Exercise, MuscleGroup, BodyMeasurement,BodyComposition)


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
        body_part=row.get("body_part")
    )


def map_muscle_group(row: dict) -> MuscleGroup:
    return MuscleGroup(
        muscle_group_id=row["MuscleGroupID"],
        name=row["Name"],
    )


def map_body_measurement(row: dict) -> list[BodyMeasurement]:
    """Map one DB row with multiple columns to a list of BodyMeasurement instances."""
    measurements = []
    date = row["measurement_date"]
    
    for col in ["chest", "waist", "abdomen", "hips", "thigh", "calf", "biceps"]:
        if row[col] is not None:
            measurements.append(
                BodyMeasurement(
                    date=date,
                    measurement_type=col,
                    value=row[col]
                )
            )
    return measurements


def map_body_composition(row: dict) -> BodyComposition:
    return BodyComposition(
        date=row["measurement_date"],
        weight=row["weight"],
        muscle_mass = row["muscle_mass"], 
        fat_mass = row["fat_mass"], 
        water_mass = row["water_mass"],
        fat_percentage=row["body_fat_percentage"],
        method = row["method"]
    )
