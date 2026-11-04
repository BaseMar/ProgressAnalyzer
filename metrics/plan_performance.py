"""Observed exercise performance and prescribed targets, without recommendations."""

from datetime import date
from math import isclose

from metrics.plan_adherence import compute_plan_adherence
from metrics.utils import set_duration_seconds, set_reps, set_weight
from models.plan_adherence import PlanAdherenceInput


def comparison_context(slot, position, planned, actual_id):
    """Shared identity used by both analytical comparisons and progression."""
    return (slot.name, slot.scheduled_date.weekday(), slot.position, position, planned.exercise_id,
            actual_id, planned.target_unit, planned.set_count, planned.target_min, planned.target_max, planned.target_rir)


def _target_result(sets, planned):
    values = [set_duration_seconds(item) if planned.target_unit == "seconds" else set_reps(item) for item in sets]
    in_range = sum(planned.target_min <= value <= planned.target_max for value in values)
    below = sum(value < planned.target_min for value in values)
    above = sum(value > planned.target_max for value in values)
    missing = planned.set_count - len(sets)
    rir = [item.rir for item in sets]
    known = [value for value in rir if value is not None]
    if planned.target_rir is None:
        rir_status = "Not specified"
    elif not sets:
        rir_status = "No sets recorded"
    elif len(known) != len(sets):
        rir_status = "Incomplete RIR data"
    elif all(value == planned.target_rir for value in known):
        rir_status = "At target"
    elif all(value < planned.target_rir for value in known):
        rir_status = "Below target (less reserve)"
    elif all(value > planned.target_rir for value in known):
        rir_status = "Above target (more reserve)"
    else:
        rir_status = "Mixed RIR"
    return {
        "in_range": in_range, "below_range": below, "above_range": above, "missing_sets": missing,
        "range_met": not missing and in_range == planned.set_count,
        "rir_status": rir_status, "rir_known_sets": len(known),
        "avg_rir": sum(known) / len(known) if known and len(known) == len(sets) else None,
        "sets": tuple({"reps": set_reps(item), "weight": set_weight(item),
                       "seconds": set_duration_seconds(item), "rir": item.rir,
                       "is_warmup": item.is_warmup} for item in sets),
    }


def _comparison(current, previous):
    result = {"previous": previous, "reps_delta": None, "seconds_delta": None, "rir_delta": None}
    if not current["sets"]:
        result["comparison"] = "No recorded sets"
    elif previous is None:
        result["comparison"] = "No previous comparable workout"
    elif current["missing_sets"] or previous["missing_sets"]:
        result["comparison"] = "Not comparable: incomplete set count"
    else:
        same_load = all(isclose(now["weight"], old["weight"], rel_tol=0, abs_tol=1e-6)
                        for now, old in zip(current["sets"], previous["sets"]))
        if not same_load:
            result["comparison"] = "Load changed: inspect individual sets"
        else:
            field = "seconds" if current["unit"] == "seconds" else "reps"
            delta = sum(item[field] for item in current["sets"]) - sum(item[field] for item in previous["sets"])
            result[f"{field}_delta"] = delta
            result["comparison"] = f'{"More" if delta > 0 else "Fewer" if delta < 0 else "Same"} {"seconds" if field == "seconds" else "reps"} at the same load'
        if current["avg_rir"] is not None and previous["avg_rir"] is not None:
            result["rir_delta"] = current["avg_rir"] - previous["avg_rir"]
    return result


def compute_plan_performance(data: PlanAdherenceInput, *, as_of: date, start: date | None = None, end: date | None = None) -> list[dict]:
    """Compare consecutive logged executions of the same plan context.

    Context includes workout name/weekday/order, exercise position, actual
    catalog ID, unit, set count, range and target RIR. A target change starts a
    new comparison history. An approved replacement retains its own catalog ID.
    Missing workouts do not erase history; incomplete executions are displayed
    but are not assigned a misleading improvement/regression label.
    """
    adherence = compute_plan_adherence(data, as_of=as_of)
    rows = {(row["day_id"], row["scheduled_date"]): row for row in adherence["workouts"]}
    session_order = {sid: index for index, sid in enumerate(data.session_order)}
    ordered = sorted(data.workouts, key=lambda item: (
        item.slot.performed_on or date.max,
        session_order.get(item.slot.session_id, item.slot.session_id or 0), item.slot.day_id,
    ))
    history = {}
    output = []
    for workout in ordered:
        slot = workout.slot
        details = rows[(slot.day_id, slot.scheduled_date)]["details"]
        for position, (target, detail) in enumerate(zip(workout.targets, details), start=1):
            planned = target.exercise
            actual_id = detail["replacement_exercise_id"] or planned.exercise_id
            context = comparison_context(slot, position, planned, actual_id)
            current = {
                "context": context,
                "day_id": slot.day_id, "plan_exercise_id": target.plan_exercise_id,
                "scheduled_date": slot.scheduled_date, "performed_on": slot.performed_on,
                "session_id": slot.session_id, "workout": slot.name,
                "planned_exercise_id": planned.exercise_id, "actual_exercise_id": actual_id,
                "unit": planned.target_unit, "planned_sets": planned.set_count,
                "target_min": planned.target_min, "target_max": planned.target_max,
                "target_rir": planned.target_rir,
                **_target_result(detail["credited_sets"], planned),
            }
            previous = history.get(context) if current["sets"] else None
            output.append({**current, **_comparison(current, previous)})
            if current["sets"]:
                history[context] = current
    return [row for row in output if (start is None or row["scheduled_date"] >= start)
            and (end is None or row["scheduled_date"] <= end)]
