from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class WorkoutSession:
    session_id: int
    session_date: date
    start_time: time | None
    end_time: time | None
