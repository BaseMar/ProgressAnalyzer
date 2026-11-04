"""Plan execution, separate from strength progress and target-range success."""

from collections import defaultdict
from datetime import date

from metrics.utils import is_duration_set, set_reps
from models.plan_adherence import PlanAdherenceInput


def compatible_set(workout_set, unit):
    return is_duration_set(workout_set) if unit == "seconds" else not is_duration_set(workout_set) and set_reps(workout_set) > 0


def compute_plan_adherence(data: PlanAdherenceInput, *, as_of: date) -> dict:
    """Count each recorded set at most once, capped at the planned set count.

    Explicit matches reserve the entire recorded exercise; remaining exact-ID
    sets are allocated in plan order. Set coverage tracks logged work, not
    technique, RIR or successful completion of the target repetition range.
    Ratios include only scheduled dates before as_of (finished calendar days).
    """
    recorded_by_session = defaultdict(list)
    for item in data.recorded:
        recorded_by_session[item.session_id].append(item)
    matches = {(item.session_id, item.plan_exercise_id): item.workout_exercise_id for item in data.matches}
    rows = []
    for workout in data.workouts:
        slot = workout.slot
        linked = slot.session_id is not None and slot.performed_on is not None and slot.performed_on <= as_of
        actual = sorted(recorded_by_session[slot.session_id], key=lambda item: item.workout_exercise_id) if linked else []
        reserved = {matches[(slot.session_id, target.plan_exercise_id)] for target in workout.targets
                    if (slot.session_id, target.plan_exercise_id) in matches}
        by_id = {item.workout_exercise_id: item for item in actual}
        pools = defaultdict(list)
        for item in actual:
            if item.workout_exercise_id not in reserved:
                for index, recorded_set in enumerate(sorted(item.sets, key=lambda value: value.set_number)):
                    pools[item.exercise_id].append((item.workout_exercise_id, index, recorded_set))
        used = set()
        details = []
        for target in workout.targets:
            planned = target.exercise
            explicit_id = matches.get((slot.session_id, target.plan_exercise_id))
            replacement = by_id.get(explicit_id)
            if explicit_id is not None:
                candidates = [(replacement.workout_exercise_id, index, item) for index, item in enumerate(replacement.sets)] if replacement else []
            else:
                candidates = pools[planned.exercise_id]
            credited = []
            for we_id, index, item in candidates:
                if (we_id, index) in used or not compatible_set(item, planned.target_unit):
                    continue
                if len(credited) >= planned.set_count:
                    break
                used.add((we_id, index))
                credited.append(item)
            details.append({
                "plan_exercise_id": target.plan_exercise_id, "exercise_id": planned.exercise_id,
                "planned_sets": planned.set_count, "covered_sets": len(credited),
                "replacement_exercise_id": replacement.exercise_id if replacement and replacement.exercise_id != planned.exercise_id else None,
                "matched_workout_exercise_id": explicit_id,
            })
        planned_sets = sum(item["planned_sets"] for item in details)
        covered_sets = sum(item["covered_sets"] for item in details)
        complete = bool(details) and covered_sets == planned_sets
        if complete:
            status = "Completed"
        elif covered_sets:
            status = "Partial"
        elif linked:
            status = "No matching work"
        elif slot.scheduled_date < as_of:
            status = "Not recorded"
        else:
            status = "Due today" if slot.scheduled_date == as_of else "Planned"
        rows.append({
            "day_id": slot.day_id, "scheduled_date": slot.scheduled_date, "name": slot.name,
            "session_id": slot.session_id, "performed_on": slot.performed_on,
            "eligible": slot.scheduled_date < as_of, "linked": linked,
            "on_time": linked and slot.scheduled_date == slot.performed_on,
            "status": status, "complete": complete,
            "planned_sets": planned_sets, "covered_sets": covered_sets,
            "planned_exercises": len(details), "covered_exercises": sum(item["covered_sets"] > 0 for item in details),
            "details": details,
        })
    eligible = [row for row in rows if row["eligible"]]
    summary = {
        "due_workouts": len(eligible),
        "linked_workouts": sum(row["linked"] for row in eligible),
        "complete_workouts": sum(row["complete"] for row in eligible),
        "on_time_workouts": sum(row["on_time"] for row in eligible),
    }
    for name in ("planned_sets", "covered_sets", "planned_exercises", "covered_exercises"):
        summary[name] = sum(row[name] for row in eligible)
    return {"summary": summary, "workouts": rows}
