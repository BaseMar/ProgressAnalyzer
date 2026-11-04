"""Snapshots consumed by pure plan adherence calculations."""

from dataclasses import dataclass

from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise
from models.workout_set import WorkoutSet


@dataclass(frozen=True)
class PlannedTarget:
    plan_exercise_id: int
    exercise: PlannedExercise


@dataclass(frozen=True)
class PlannedWorkout:
    slot: ScheduledWorkout
    targets: tuple[PlannedTarget, ...]


@dataclass(frozen=True)
class RecordedExercise:
    workout_exercise_id: int
    session_id: int
    exercise_id: int
    sets: tuple[WorkoutSet, ...]


@dataclass(frozen=True)
class ExerciseMatch:
    session_id: int
    plan_exercise_id: int
    workout_exercise_id: int


@dataclass(frozen=True)
class PlanAdherenceInput:
    workouts: tuple[PlannedWorkout, ...]
    recorded: tuple[RecordedExercise, ...]
    matches: tuple[ExerciseMatch, ...]
