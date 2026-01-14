from models import (WorkoutSession, WorkoutExercise, WorkoutSet, Exercise, MuscleGroup, BodyMeasurement,BodyComposition)


def map_workout_session(row: dict) -> WorkoutSession:
    return WorkoutSession(
        session_id=row["SessionID"],
        session_date=row["SessionDate"],
        start_time=row.get("StartTime"),
        end_time=row.get("EndTime"),
    )


def map_workout_exercise(row: dict) -> WorkoutExercise:
    return WorkoutExercise(
        workout_exercise_id=row["WorkoutExerciseID"],
        session_id=row["SessionID"],
        exercise_id=row["ExerciseID"],
    )


def map_workout_set(row: dict) -> WorkoutSet:
    return WorkoutSet(
        workout_exercise_id=row["WorkoutExerciseID"],
        set_number=row["SetNumber"],
        repetitions=row["Repetitions"],
        weight=row["Weight"],
        rir=row.get("RIR"),
    )


def map_exercise(row: dict) -> Exercise:
    return Exercise(
        exercise_id=row["ExerciseID"],
        name=row["ExerciseName"],
        primary_muscle_group_id=None, #row.get("PrimaryMuscleGroupID"),
        body_part=row.get("BodyPart")
    )


def map_muscle_group(row: dict) -> MuscleGroup:
    return MuscleGroup(
        muscle_group_id=row["MuscleGroupID"],
        name=row["Name"],
    )


def map_body_measurement(row: dict) -> list[BodyMeasurement]:
    """Map one DB row with multiple columns to a list of BodyMeasurement instances."""
    measurements = []
    date = row["MeasurementDate"]
    
    for col in ["Chest", "Waist", "Abdomen", "Hips", "Thigh", "Calf", "Biceps"]:
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
        date=row["MeasurementDate"],
        weight=row["Weight"],
        muscle_mass = row["MuscleMass"], 
        fat_mass = row["FatMass"], 
        water_mass = row["WaterMass"],
        fat_percentage=row["BodyFatPercentage"],
        method = row["Method"]
    )
