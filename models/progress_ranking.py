"""Window-based exercise trends, distinct from latest-pair observations."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ExerciseTrend:
    exercise_id: int
    name: str
    measure: str
    baseline: float
    current: float
    change_pct: float
    sessions: int
    window: int
    baseline_dates: tuple[date, ...]
    current_dates: tuple[date, ...]


@dataclass(frozen=True)
class ProgressRanking:
    trends: tuple[ExerciseTrend, ...]
    unavailable_exercise_ids: tuple[int, ...]
