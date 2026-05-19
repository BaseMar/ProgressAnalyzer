from metrics.input import MetricsInput

from mapper import map_body_composition, map_body_measurement
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.workout_set import WorkoutSet
from models.exercise import Exercise


class MetricsInputBuilder:
    """
    Translates raw DataFrames from DataManager into domain models
    required by the metrics engine.
    """

    @staticmethod
    def build(
        sessions_df,
        exercises_df,
        sets_df,
        body_measurements_df,
        body_composition_df,
    ) -> MetricsInput:

        sessions = [
            WorkoutSession(
                session_id=row.session_id,
                session_date=row.session_date,
                start_time=getattr(row, "start_time", None),
                end_time=getattr(row, "end_time", None),
            )
            for row in sessions_df.itertuples()
        ]

        workout_exercises = [
            WorkoutExercise(
                workout_exercise_id=row.workout_exercise_id,
                session_id=row.session_id,
                exercise_id=row.exercise_id,
            )
            for row in sets_df.drop_duplicates("workout_exercise_id").itertuples()
        ]

        sets = [
            WorkoutSet(
                workout_exercise_id=row.workout_exercise_id,
                set_number=row.set_number,
                repetitions=row.repetitions,
                weight=row.weight,
                rir=getattr(row, "rir", None),
            )
            for row in sets_df.itertuples()
        ]

        exercises = [
            Exercise(
                exercise_id=row.exercise_id,
                name=row.exercise_name,
                primary_muscle_group_id=getattr(row, "primary_muscle_group_id", None),
                body_part=getattr(row, "body_part", None),
            )
            for row in exercises_df.itertuples()
        ]

        body_measurements = [
            measurement
            for row in body_measurements_df.to_dict("records")
            for measurement in map_body_measurement(row)
        ]

        body_composition = [
            map_body_composition(row)
            for row in body_composition_df.to_dict("records")
        ]

        return MetricsInput(
            sessions=sessions,
            workout_exercises=workout_exercises,
            sets=sets,
            exercises=exercises,
            exercise_muscle_targets=[],
            muscle_groups=[],
            body_measurements=body_measurements,
            body_composition=body_composition,
        )
