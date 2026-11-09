"""Normalize recorded dates without importing measurement summary calculations."""
from datetime import date, datetime
from typing import Any


def to_date(value: Any) -> date:
    """Normalize date-like values to ``datetime.date`` for reliable joins."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Unsupported date value: {value!r}")
