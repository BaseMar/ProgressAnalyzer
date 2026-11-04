"""Immutable plan snapshots, independent of the UI and database."""

from dataclasses import dataclass
from datetime import date
from math import isfinite


def _positive_int(value: int, label: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer")


@dataclass(frozen=True)
class PlannedExercise:
    exercise_id: int
    set_count: int
    target_min: int
    target_max: int
    target_unit: str = "reps"
    target_rir: int | None = None
    weight_increment: float | None = None

    def __post_init__(self):
        for label in ("exercise_id", "set_count", "target_min", "target_max"):
            _positive_int(getattr(self, label), label)
        if self.target_min > self.target_max:
            raise ValueError("Target minimum cannot exceed maximum")
        if self.target_unit not in ("reps", "seconds"):
            raise ValueError("Target unit must be reps or seconds")
        if self.target_rir is not None and (type(self.target_rir) is not int or self.target_rir < 0):
            raise ValueError("Target RIR must be a non-negative integer or None")
        if self.weight_increment is not None and (
            isinstance(self.weight_increment, bool)
            or not isfinite(self.weight_increment) or self.weight_increment <= 0
        ):
            raise ValueError("Weight increment must be finite and positive")


@dataclass(frozen=True)
class TrainingDay:
    name: str
    weekday: int  # Monday = 0, Sunday = 6
    exercises: tuple[PlannedExercise, ...]

    def __post_init__(self):
        if not self.name.strip() or len(self.name) > 120:
            raise ValueError("Training day name must contain 1–120 characters")
        if type(self.weekday) is not int or not 0 <= self.weekday <= 6:
            raise ValueError("Weekday must be between 0 (Monday) and 6 (Sunday)")
        if not isinstance(self.exercises, tuple) or not self.exercises:
            raise ValueError("A training day must contain a non-empty tuple of exercises")
        if not all(isinstance(item, PlannedExercise) for item in self.exercises):
            raise ValueError("Invalid planned exercise")


@dataclass(frozen=True)
class TrainingPlanDraft:
    name: str
    effective_from: date
    days: tuple[TrainingDay, ...]

    def __post_init__(self):
        if not self.name.strip() or len(self.name) > 120:
            raise ValueError("Plan name must contain 1–120 characters")
        if type(self.effective_from) is not date:
            raise ValueError("Plan effective date must be a date")
        if not isinstance(self.days, tuple) or not self.days:
            raise ValueError("A plan must contain a non-empty tuple of training days")
        if not all(isinstance(day, TrainingDay) for day in self.days):
            raise ValueError("Invalid training day")


@dataclass(frozen=True)
class TrainingPlanVersion:
    plan_id: int
    version_id: int
    version_number: int
    draft: TrainingPlanDraft
