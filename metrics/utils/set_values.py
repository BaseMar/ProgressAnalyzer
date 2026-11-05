from __future__ import annotations

import math
from typing import Any

from metrics.utils.strength import estimate_1rm
from metrics.set_interpretation import interpret_sets
from metrics.load_metrics import load_type, total_load_kg


def analysis_sets(sets, *, progression=False, deload_exercise_ids=frozenset()):
    """Separate descriptive workload from eligible ordinary/timed progression."""
    sets = tuple(sets)
    interpretations = interpret_sets(sets, deload_exercise_ids=deload_exercise_ids)
    return [item for item, meaning in zip(sets, interpretations)
            if meaning.descriptive and (not progression or meaning.progression_eligible)]


def _number_or_default(value: Any, default: int | float = 0) -> Any:
    if value is None:
        return default

    try:
        if math.isnan(float(value)):
            return default
    except (TypeError, ValueError):
        pass

    return value


def set_reps(workout_set: Any) -> int:
    return int(_number_or_default(getattr(workout_set, "repetitions", None), 0))


def set_weight(workout_set: Any) -> float:
    return float(_number_or_default(getattr(workout_set, "weight", None), 0))


def set_duration_seconds(workout_set: Any) -> int:
    return int(_number_or_default(getattr(workout_set, "duration_seconds", None), 0))


def is_duration_set(workout_set: Any) -> bool:
    return set_duration_seconds(workout_set) > 0


def set_volume(workout_set: Any) -> float:
    if is_duration_set(workout_set):
        return 0.0
    load = total_load_kg(workout_set)
    return set_reps(workout_set) * load if load is not None else 0.0


def set_intensity(workout_set: Any) -> float | None:
    if is_duration_set(workout_set) or load_type(workout_set) in ("bodyweight", "assisted_bodyweight"):
        return None
    return set_weight(workout_set) * (1 + set_reps(workout_set) / 30)


def set_estimated_1rm(workout_set: Any) -> float | None:
    if is_duration_set(workout_set) or load_type(workout_set) in ("bodyweight", "assisted_bodyweight"):
        return None
    return estimate_1rm(set_weight(workout_set), set_reps(workout_set))


def set_effective_sets(workout_set: Any) -> float:
    # Historical alias: count recorded sets, never turn seconds into hard sets.
    return 1.0


def load_summary(sets):
    dynamic = [item for item in sets if not is_duration_set(item)]
    missing = sum(total_load_kg(item) is None for item in dynamic)
    return {"dynamic_sets": len(dynamic), "timed_sets": len(sets) - len(dynamic),
            "unknown_load_sets": missing, "volume_complete": missing == 0,
            "unknown_total_load_sets": sum(total_load_kg(item) is None for item in sets)}
