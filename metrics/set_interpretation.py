"""Transparent effort policy. Interpret records without rewriting labels or RIR."""

from collections import defaultdict
from math import isfinite

from metrics.load_metrics import load_type, total_load_kg
from models.set_interpretation import SetInterpretation


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value) if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _timed(item):
    duration = _number(item.duration_seconds)
    return duration is not None and duration > 0


def _known_working(item):
    if item.is_warmup is True or _timed(item):
        return False
    rir = _number(item.rir)
    load = _number(item.weight)
    if load is None or load < 0 or (item.rir is not None and (rir is None or rir < 0)):
        return False
    return item.is_warmup is False or (rir is not None and 0 <= rir <= 3)


def interpret_sets(sets, *, deload_exercise_ids=frozenset()):
    """Classify within each logged exercise, independently of input-list order.

    Explicit corrections win. Otherwise RIR 0–3 is working, 4–5 light, >5 low
    effort, and absent RIR unknown. A light set is only a likely warm-up when it
    precedes every known working set and its load is below the first such set.
    Deload and timed work do not need repetition-based RIR for coverage.
    """
    sets = tuple(sets)
    groups = defaultdict(list)
    for item in sets:
        groups[item.workout_exercise_id].append(item)
    first_work = {}
    for exercise_id, items in groups.items():
        working = sorted(
            (item for item in items if _known_working(item)), key=lambda item: item.set_number
        )
        if working:
            first_work[exercise_id] = working[0]
    output = []
    for item in sets:
        if item.is_warmup is True:
            output.append(SetInterpretation("warmup", "explicit", "explicit_warmup"))
            continue
        load = _number(item.weight)
        if load is None or load < 0:
            output.append(SetInterpretation("invalid", "validation", "invalid_load"))
            continue
        deload = item.workout_exercise_id in deload_exercise_ids
        if _timed(item):
            output.append(
                SetInterpretation(
                    "deload" if deload else "timed",
                    "plan" if deload else "duration",
                    "scheduled_deload" if deload else "duration_recorded",
                    not deload,
                )
            )
            continue
        rir = _number(item.rir)
        if item.rir is not None and (rir is None or rir < 0):
            output.append(SetInterpretation("invalid", "validation", "invalid_rir"))
        elif deload:
            output.append(SetInterpretation("deload", "plan", "scheduled_deload"))
        elif item.is_warmup is False:
            output.append(
                SetInterpretation("working", "explicit", "explicit_working", rir is not None)
            )
        elif rir is None:
            output.append(SetInterpretation("unknown", "unknown", "missing_rir"))
        elif rir <= 3:
            output.append(SetInterpretation("working", "rir", "rir_0_3", True))
        elif rir <= 5:
            first = first_work.get(item.workout_exercise_id)
            first_load = total_load_kg(first) if first is not None else None
            actual_load = total_load_kg(item)
            warmup = (
                first is not None
                and first.set_number > item.set_number
                and first_load is not None
                and actual_load is not None
                and load_type(first) == load_type(item)
                and actual_load < first_load
            )
            output.append(
                SetInterpretation(
                    "warmup" if warmup else "light",
                    "sequence" if warmup else "rir",
                    "lighter_before_working" if warmup else "rir_4_5",
                )
            )
        else:
            output.append(SetInterpretation("low_effort", "rir", "rir_above_5"))
    return tuple(output)
