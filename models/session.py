from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Session:
    session_id: int
    date: date
    start_time: time | None
    end_time: time | None
