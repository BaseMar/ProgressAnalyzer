"""Observed exercise performance and prescribed targets, without recommendations."""

from datetime import date
from math import isclose

from metrics.plan_adherence import compute_plan_adherence
from metrics.training_block import deload_adjusted_input, is_deload_workout
from metrics.utils import set_duration_seconds, set_reps, set_weight
from models.plan_adherence import PlanAdherenceInput
from models.progression import DeloadPolicy


def comparison_context(slot, position, planned, actual_id):
    """Shared identity used by both analytical comparisons and progression."""
    return (slot.name, slot.scheduled_date.weekday(), slot.position, position, planned.exercise_id,
            actual_id, planned.target_unit, planned.set_count, planned.target_min, planned.target_max, planned.target_rir)


def _target_result(sets, planned, interpretations):
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
        "progression_eligible": bool(sets) and all(meaning.progression_eligible for meaning in interpretations),
        "sets": tuple({"reps": set_reps(item), "weight": set_weight(item),
                       "seconds": set_duration_seconds(item), "rir": item.rir,
                       "is_warmup": item.is_warmup, "set_kind": meaning.kind,
                       "classification_source": meaning.source, "classification_reason": meaning.reason,
                       "progression_eligible": meaning.progression_eligible}
                      for item, meaning in zip(sets, interpretations)),
    }


def _comparison(current, previous):
    result = {"previous": previous, "reps_delta": None, "seconds_delta": None, "rir_delta": None}
    if not current["sets"]:
        excluded = current.get("excluded_set_kinds", ())
        result["comparison"] = ("Light/low-effort work: outside ordinary progression assessment"
                                if any(kind in excluded for kind in ("light", "low_effort")) else "No recorded sets")
    elif previous is None:
        result["comparison"] = "No previous comparable workout"
    elif current["missing_sets"] or previous["missing_sets"]:
        result["comparison"] = "Not comparable: incomplete set count"
    elif not current["progression_eligible"] or not previous["progression_eligible"]:
        result["comparison"] = "Not comparable: missing or insufficient ordinary effort evidence"
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


def compute_plan_performance(data: PlanAdherenceInput, *, as_of: date, start: date | None = None, end: date | None = None,
                             settings_by_version=None, deload_policy=DeloadPolicy()) -> list[dict]:
    """Compare consecutive logged executions of the same plan context.

    Context includes workout name/weekday/order, exercise position, actual
    catalog ID, unit, set count, range and target RIR. A target change starts a
    new comparison history. An approved replacement retains its own catalog ID.
    Missing workouts do not erase history; incomplete executions are displayed
    but are not assigned a misleading improvement/regression label.
    """
    settings_by_version = settings_by_version or {}
    adjusted = deload_adjusted_input(data, settings_by_version, deload_policy, as_of=as_of)
    effective = {(item.slot.day_id, item.slot.scheduled_date): item for item in adjusted.workouts}
    adherence = compute_plan_adherence(adjusted, as_of=as_of, settings_by_version=settings_by_version)
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
        deload = is_deload_workout(slot, settings_by_version.get(slot.version_id), as_of=as_of)
        details = rows[(slot.day_id, slot.scheduled_date)]["details"]
        for position, (target, detail) in enumerate(zip(workout.targets, details), start=1):
            planned = target.exercise
            actual_id = detail["replacement_exercise_id"] or planned.exercise_id
            context = comparison_context(slot, position, planned, actual_id)
            expected = effective[(slot.day_id, slot.scheduled_date)].targets[position - 1].exercise
            current = {
                "context": context,
                "day_id": slot.day_id, "version_id": slot.version_id, "plan_exercise_id": target.plan_exercise_id,
                "scheduled_date": slot.scheduled_date, "performed_on": slot.performed_on,
                "session_id": slot.session_id, "workout": slot.name,
                "planned_exercise_id": planned.exercise_id, "actual_exercise_id": actual_id,
                "training_phase": "deload" if deload else "normal",
                "unit": expected.target_unit, "planned_sets": expected.set_count,
                "target_min": expected.target_min, "target_max": expected.target_max,
                "target_rir": expected.target_rir,
                "excluded_set_kinds": detail["excluded_set_kinds"],
                **_target_result(detail["credited_sets"], expected, detail["set_interpretations"]),
            }
            previous = history.get(context) if current["sets"] else None
            comparison = _comparison(current, previous)
            if deload:
                comparison = {"previous": None, "reps_delta": None, "seconds_delta": None, "rir_delta": None,
                              "comparison": "Deload: reduced training demand; excluded from progression comparisons"}
            output.append({**current, **comparison})
            if current["sets"] and not deload:
                history[context] = current
    return [row for row in output if (start is None or row["scheduled_date"] >= start)
            and (end is None or row["scheduled_date"] <= end)]
