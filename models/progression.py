"""Derived training targets, not edits to plans or logged performances."""
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Literal

RULES_VERSION = "double-progression-2026-11-v1"

RecommendationAction = Literal[
    "increase_reps", "increase_time", "equalize_weight", "increase_weight",
    "reduce_weight", "maintain", "deload", "insufficient_data",
]


@dataclass(frozen=True)
class DeloadPolicy:
    retained_set_fraction: float = 1.0
    load_reduction: float = 0.30
    max_load_reduction: float = 0.40
    minimum_rir: int = 3
    extra_rir: int = 1
    maximum_rir: int = 4

    def __post_init__(self):
        for name in ("retained_set_fraction", "load_reduction", "max_load_reduction"):
            value = getattr(self, name)
            upper_valid = value <= 1 if name == "retained_set_fraction" and isinstance(value, (int, float)) else isinstance(value, (int, float)) and value < 1
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0 or not upper_valid:
                raise ValueError(f"{name} must be a finite valid fraction")
        if self.load_reduction > self.max_load_reduction:
            raise ValueError("Load reduction cannot exceed its limit")
        for name in ("minimum_rir", "extra_rir"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.maximum_rir) is not int or self.maximum_rir < self.minimum_rir:
            raise ValueError("Maximum deload RIR must be at least the minimum")


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
    confirmations_required: int = 1
    max_history_gap_days: int = 21
    max_relative_weight_increase: float = 0.10
    plateau_exposures: int = 4
    timed_increment_seconds: int = 5

    def __post_init__(self):
        if type(self.confirmations_required) is not int or self.confirmations_required < 1:
            raise ValueError("At least one upper-range execution is required")
        if type(self.max_history_gap_days) is not int or self.max_history_gap_days < 1:
            raise ValueError("History gap must be a positive number of days")
        if type(self.plateau_exposures) is not int or self.plateau_exposures < 3:
            raise ValueError("Plateau assessment needs at least three executions")
        if type(self.timed_increment_seconds) is not int or self.timed_increment_seconds < 1:
            raise ValueError("Time increment must be a positive number of seconds")
        if (isinstance(self.max_relative_weight_increase, bool)
            or not isinstance(self.max_relative_weight_increase, (int, float))
            or not isfinite(self.max_relative_weight_increase)
            or not 0 < self.max_relative_weight_increase <= 1):
            raise ValueError("Relative increase limit must be finite and between 0 and 1")


@dataclass(frozen=True)
class SetGoal:
    weight: float | None
    minimum: int
    maximum: int
    unit: Literal["reps", "seconds"]
    load_type: str = "legacy"
    assistance_kg: float | None = None


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
    notices: tuple[str, ...] = ()
    rules_version: str = RULES_VERSION
    target_rir_max: int | None = None


@dataclass(frozen=True)
class WorkoutRecommendation:
    block: TrainingBlockPhase
    exercises: tuple[ExerciseRecommendation, ...]
    rules_version: str = RULES_VERSION
