from dataclasses import dataclass

from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.workout_set import WorkoutSet
from models.exercise import Exercise
from models.muscle_group import MuscleGroup
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
    muscle_groups: list[MuscleGroup]

    body_measurements: list[BodyMeasurement]
    body_composition: list[BodyComposition]
