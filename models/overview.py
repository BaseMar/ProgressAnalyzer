"""Prepared content for the current-plan landing page."""

from dataclasses import dataclass

from models.progression import ExerciseRecommendation


@dataclass(frozen=True)
class OverviewConclusion:
    title: str
    detail: str
    kind: str = "neutral"


@dataclass(frozen=True)
class RecommendationGap:
    count: int
    example: ExerciseRecommendation


@dataclass(frozen=True)
class WorkoutFocus:
    visible: tuple[ExerciseRecommendation, ...]
    available: int
    total: int
    gaps: tuple[RecommendationGap, ...] = ()
