from dataclasses import dataclass
from typing import List, Optional

from models.session import WorkoutSession, WorkoutExercise, WorkoutSet
from models.exercise import Exercise
from models.body import BodyComposition, BodyMeasurement


@dataclass(frozen=True)
class MetricsInput:
    """Input data structure for metrics computations."""

    # --- training ---
    sessions: List[WorkoutSession]
    workout_exercises: List[WorkoutExercise]
    sets: List[WorkoutSet]
    exercises: List[Exercise]

    # --- body ---
    body_composition: Optional[List[BodyComposition]] = None
    body_measurements: Optional[List[BodyMeasurement]] = None
