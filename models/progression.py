"""Derived training targets, not edits to plans or logged performances."""
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Literal

RecommendationAction = Literal["increase_reps", "increase_weight", "maintain", "deload", "insufficient_data"]


@dataclass(frozen=True)
class DeloadPolicy:
    retained_set_fraction: float = 0.5
    load_reduction: float = 0.10
    max_load_reduction: float = 0.20
    minimum_rir: int = 4
    extra_rir: int = 2

    def __post_init__(self):
        for name in ("retained_set_fraction", "load_reduction", "max_load_reduction"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 < value < 1:
                raise ValueError(f"{name} must be finite and between 0 and 1")
        if self.load_reduction > self.max_load_reduction:
            raise ValueError("Load reduction cannot exceed its limit")
        for name in ("minimum_rir", "extra_rir"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class TrainingBlockPhase:
    phase: Literal["unconfigured", "not_started", "normal", "deload"]
    cycle: int | None = None
    week: int | None = None
    cycle_start: date | None = None
    cycle_end: date | None = None
    deload_start: date | None = None


@dataclass(frozen=True)
class ProgressionPolicy:
    confirmations_required: int = 2
    max_history_gap_days: int = 21
    max_relative_weight_increase: float = 0.10

    def __post_init__(self):
        if type(self.confirmations_required) is not int or self.confirmations_required < 2:
            raise ValueError("At least two upper-range confirmations are required")
        if type(self.max_history_gap_days) is not int or self.max_history_gap_days < 1:
            raise ValueError("History gap must be a positive number of days")
        if (isinstance(self.max_relative_weight_increase, bool)
            or not isinstance(self.max_relative_weight_increase, (int, float))
            or not isfinite(self.max_relative_weight_increase)
            or not 0 < self.max_relative_weight_increase <= 1):
            raise ValueError("Relative increase limit must be finite and between 0 and 1")


@dataclass(frozen=True)
class SetGoal:
    weight: float
    minimum: int
    maximum: int
    unit: Literal["reps", "seconds"]


@dataclass(frozen=True)
class ExerciseRecommendation:
    plan_exercise_id: int
    planned_exercise_id: int
    actual_exercise_id: int
    scheduled_date: date
    action: RecommendationAction
    goals: tuple[SetGoal, ...]
    target_rir: int | None
    reason_code: str
    reason: str
    evidence_session_ids: tuple[int, ...] = ()
    evidence_dates: tuple[date, ...] = ()
    evidence_workouts: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkoutRecommendation:
    block: TrainingBlockPhase
    exercises: tuple[ExerciseRecommendation, ...]
