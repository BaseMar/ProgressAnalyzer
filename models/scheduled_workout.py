"""A dated occurrence of a versioned workout template."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ScheduledWorkout:
    day_id: int
    version_id: int
    scheduled_date: date
    name: str
    session_id: int | None = None
    performed_on: date | None = None
    position: int = 1
