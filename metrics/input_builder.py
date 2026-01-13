from metrics.input import MetricsInput

from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.workout_set import WorkoutSet
from models.exercise import Exercise
from models.body_measurement import BodyMeasurement
from models.body_composition import BodyComposition


class MetricsInputBuilder:
    """
    Translates raw DataFrames from DataManager into domain models
    required by the metrics engine.
    """

    @staticmethod
    def build(sessions_df, exercises_df, sets_df, body_measurements_df, body_composition_df,) -> MetricsInput:

        sessions = [WorkoutSession(
                session_id=row.SessionID,
                date=row.SessionDate,
                start_time=row.StartTime,
                end_time=row.EndTime,)
            for row in sessions_df.itertuples()]

        workout_exercises = [WorkoutExercise(
                workout_exercise_id=row.WorkoutExerciseID,
                session_id=row.SessionID,
                exercise_id=row.ExerciseID,)
            for row in sets_df.drop_duplicates("WorkoutExerciseID").itertuples()]

        sets = [WorkoutSet(
                workout_exercise_id=row.WorkoutExerciseID,
                set_number=row.SetNumber,
                repetitions=row.Repetitions,
                weight=row.Weight,
                rir=row.RIR,)
            for row in sets_df.itertuples()]

        exercises = [Exercise(
                exercise_id=row.ExerciseID,
                name=row.ExerciseName,
                category=row.Category,
                body_part=row.BodyPart,)
            for row in exercises_df.itertuples()]

        body_measurements = [BodyMeasurement(**row._asdict()) for row in body_measurements_df.itertuples(index=False)]

        body_composition = [BodyComposition(**row._asdict()) for row in body_composition_df.itertuples(index=False)]

        return MetricsInput(
            sessions=sessions,
            workout_exercises=workout_exercises,
            sets=sets,
            exercises=exercises,
            muscle_groups=[],
            body_measurements=body_measurements,
            body_composition=body_composition,
        )
