from __future__ import annotations

from typing import Any

from metrics.utils.strength import estimate_1rm


def set_reps(workout_set: Any) -> int:
    return int(workout_set.repetitions or 0)


def set_weight(workout_set: Any) -> float:
    return float(workout_set.weight or 0)


def set_duration_seconds(workout_set: Any) -> int:
    return int(getattr(workout_set, "duration_seconds", None) or 0)


def is_duration_set(workout_set: Any) -> bool:
    return set_duration_seconds(workout_set) > 0


def set_volume(workout_set: Any) -> float:
    if is_duration_set(workout_set):
        return 0.0
    return set_reps(workout_set) * set_weight(workout_set)


def set_intensity(workout_set: Any) -> float | None:
    if is_duration_set(workout_set):
        return None
    return set_weight(workout_set) * (1 + set_reps(workout_set) / 30)


def set_estimated_1rm(workout_set: Any) -> float | None:
    if is_duration_set(workout_set):
        return None
    return estimate_1rm(set_weight(workout_set), set_reps(workout_set))


def set_effective_sets(workout_set: Any) -> float:
    duration_seconds = set_duration_seconds(workout_set)
    if duration_seconds:
        return duration_seconds / 30
    return 1.0
