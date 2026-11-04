"""Calendar helpers shared by training frequency metrics."""

from datetime import date, timedelta
from typing import Iterable


def observed_week_count(dates: Iterable[date]) -> int:
    """Count ISO weeks from the first to last workout, including empty weeks.

    Without an active plan, dates before/after that observed span cannot be
    interpreted as missed workouts. Boundary weeks count as calendar weeks.
    """
    dates = list(dates)
    if not dates:
        return 0
    first, last = min(dates), max(dates)
    first_monday = first - timedelta(days=first.weekday())
    last_monday = last - timedelta(days=last.weekday())
    return (last_monday - first_monday).days // 7 + 1
