"""Immutable, auditable observations; no effectiveness score or diagnoses."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from models.plan_adherence import PlannedWorkout
from models.progression import ExerciseRecommendation, WorkoutRecommendation


@dataclass(frozen=True)
class WorkoutPreview:
    upcoming: PlannedWorkout
    recommendation: WorkoutRecommendation


@dataclass(frozen=True)
class InsightPolicy:
    max_annotations: int = 5
    max_gap_days: int = 21

    def __post_init__(self):
        if type(self.max_annotations) is not int or not 1 <= self.max_annotations <= 5:
            raise ValueError("Show between one and five annotations")
        if type(self.max_gap_days) is not int or self.max_gap_days < 1:
            raise ValueError("History gap must be a positive number of days")


@dataclass(frozen=True)
class InsightSet:
    quantity: float
    weight: float
    rir: int | None
    kind: str
    source: str
    reason: str
    load_type: str = "legacy"
    total_load_kg: float | None = None
    body_mass_kg: float | None = None
    assistance_kg: float | None = None


@dataclass(frozen=True)
class InsightSource:
    session_id: int | None
    scheduled_date: date | None
    performed_on: date | None
    workout: str
    context: tuple
    phase: str
    planned_sets: int | None
    target_min: int | None
    target_max: int | None
    target_rir: int | None
    sets: tuple[InsightSet, ...]
    excluded_kinds: tuple[str, ...]


@dataclass(frozen=True)
class TrainingInsight:
    code: str
    priority: int  # Smaller values are shown first.
    observation: str
    evidence: str
    action: str
    evidence_level: Literal["paired", "observed", "limited"]
    rule: str
    sources: tuple[InsightSource, ...]
    exercise_id: int | None = None
    next_target: str | None = None
    recommendation: ExerciseRecommendation | None = None


@dataclass(frozen=True)
class ExerciseProgressSummary:
    improving: int = 0
    unchanged: int = 0
    lower: int = 0
    unassessed: int = 0

    @property
    def compared(self):
        return self.improving + self.unchanged + self.lower


@dataclass(frozen=True)
class InsightReport:
    annotations: tuple[TrainingInsight, ...]
    assessed_contexts: int
    limited_contexts: int
    omitted_annotations: int
    exercise_progress: ExerciseProgressSummary = ExerciseProgressSummary()
    highlighted_annotations: tuple[TrainingInsight, ...] = ()
