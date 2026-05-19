from dataclasses import dataclass

from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.workout_set import WorkoutSet
from models.exercise import Exercise
from models.exercise_muscle_target import ExerciseMuscleTarget
from models.body_measurement import BodyMeasurement
from models.body_composition import BodyComposition


@dataclass(frozen=True)
class MetricsInput:
    """
    Immutable container with all data required to compute metrics.
    Acts as a contract between data layer and metrics engine.
    """

    sessions: list[WorkoutSession]
    workout_exercises: list[WorkoutExercise]
    sets: list[WorkoutSet]

    exercises: list[Exercise]
    exercise_muscle_targets: list[ExerciseMuscleTarget]
    muscle_groups: list[str]

    body_measurements: list[BodyMeasurement]
    body_composition: list[BodyComposition]
