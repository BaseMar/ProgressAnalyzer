"""Choose recorded evidence separately from strict progression comparisons."""

from collections import Counter
from dataclasses import replace
from datetime import date

from metrics.plan_performance import comparison_context, compute_plan_performance
from models.plan_adherence import PlannedTarget


def approved_alternatives(history, slot, planned_exercises, *, as_of):
    """Explicit logged alternatives for this workout survive target/order changes."""
    rows = compute_plan_performance(history, as_of=as_of)
    return {
        position: sorted(
            {
                row["actual_exercise_id"]
                for row in rows
                if row["actual_exercise_id"] != planned.exercise_id
                and row["sets"]
                and row["performed_on"] is not None
                and row["performed_on"] <= as_of
                and workout_exercise_identity(row["context"])
                == workout_exercise_identity(
                    comparison_context(slot, position, planned, row["actual_exercise_id"])
                )
            }
        )
        for position, planned in enumerate(planned_exercises, start=1)
    }


def with_recorded_baselines(data, performances, planned, actual_id, *, as_of):
    """Include exact-ID records absent from an old workout's prescription.

    A session link establishes its date, workout and block even when a recorded
    exercise wasn't in that version of the routine. Project that observation
    onto the upcoming prescription using the ordinary set interpretation rules.
    Such rows supply starting loads only; they never establish plan coverage,
    replacements or upper-range confirmations for the historical workout.
    """
    represented = {(row["session_id"], row["actual_exercise_id"]) for row in performances}
    occurrences = Counter((item.session_id, item.exercise_id) for item in data.recorded)
    workouts = {
        item.slot.session_id: item for item in data.workouts if item.slot.session_id is not None
    }
    extra = []
    for recorded in data.recorded:
        key = recorded.session_id, recorded.exercise_id
        if recorded.exercise_id != actual_id or key in represented or occurrences[key] != 1:
            continue
        workout = workouts.get(recorded.session_id)
        if workout is None:
            continue
        projected = replace(
            workout,
            targets=(
                PlannedTarget(
                    -recorded.workout_exercise_id,
                    replace(planned, exercise_id=actual_id, history_key=None),
                ),
            ),
        )
        observation = replace(data, workouts=(projected,), recorded=(recorded,), matches=())
        for row in compute_plan_performance(observation, as_of=as_of):
            extra.append({**row, "baseline_only": True})
    if not extra:
        return performances
    order = {sid: index for index, sid in enumerate(data.session_order)}
    return sorted(
        [*performances, *extra],
        key=lambda row: (
            row["performed_on"] or date.max,
            order.get(row["session_id"], row["session_id"] or 0),
            row["day_id"],
        ),
    )


def workout_exercise_identity(context):
    """An exercise's workout identity survives target and order revisions."""
    return context[0], context[1], context[2], context[4], context[6]


def changed_context_reason(latest, context, workout):
    """Explain the actual prescription changes instead of a generic reset."""
    previous = latest["context"]
    changes = []
    if latest["workout"] != workout:
        changes.append(f"Source workout: {latest['workout']}; upcoming workout: {workout}.")
    if previous[3] != context[3]:
        changes.append(f"Exercise position changed: {previous[3]} → {context[3]}.")
    if previous[7] != context[7]:
        changes.append(f"Working sets changed: {previous[7]} → {context[7]}.")
    if previous[8:10] != context[8:10]:
        changes.append(
            f"Target range changed: {previous[8]}–{previous[9]} → {context[8]}–{context[9]} {context[6]}."
        )
    if previous[10] != context[10]:
        changes.append(f"Target RIR changed: {previous[10]} → {context[10]}.")
    if not changes:
        changes.append(
            "No established ordinary execution for this exercise in the current plan position."
        )
    return (
        " ".join(changes)
        + " Choose the working loads manually using the recorded results below. Log and link the completed workout to establish the new baseline."
    )


def recommendation_history(performances, context, *, as_of, block_start):
    """Return strict history or a baseline of the exact same actual exercise.

    The latest execution in this workout takes priority, including incomplete
    or empty records. Another workout is only a baseline when this workout has
    no execution of the selected actual exercise. Different catalog IDs never
    share loads, and a changed prescription never inherits confirmations.
    """
    actual_id, unit = context[5], context[6]
    candidates = [
        row
        for row in performances
        if row["actual_exercise_id"] == actual_id
        and row["unit"] == unit
        and row["session_id"] is not None
        and row["performed_on"] is not None
        and row["performed_on"] <= as_of
        and (block_start is None or row["performed_on"] >= block_start)
    ]
    if context[1] is None and context[2] is None:
        lineage = [
            row
            for row in performances
            if row["context"][0] == context[0]
            and not row.get("baseline_only")
            and row["session_id"] is not None
            and row["performed_on"] is not None
            and row["performed_on"] <= as_of
            and (block_start is None or row["performed_on"] >= block_start)
        ]
        if lineage and lineage[-1]["context"] != context:
            # Returning to an old exercise must not bridge an intervening
            # exercise/replacement in the same stable position.
            return candidates[-1:], True
    local = [
        row
        for row in candidates
        if workout_exercise_identity(row["context"]) == workout_exercise_identity(context)
    ]
    if local:
        occurrences = Counter((row["session_id"], row["day_id"]) for row in local)
        if any(count > 1 for count in occurrences.values()):
            # Repeated positions of the same exercise have no unambiguous
            # transferable identity after order/target changes.
            return [
                row for row in local if row["context"] == context and not row.get("baseline_only")
            ], False
        latest = local[-1]
        if latest.get("baseline_only"):
            return [latest], True
        if latest["context"] == context:
            # Do not bridge an intervening prescription/order change on return.
            history = []
            for row in reversed(local):
                if row["context"] != context or row.get("baseline_only"):
                    break
                history.append(row)
            return list(reversed(history)), False
        return [latest], True
    return (candidates[-1:], True) if candidates else ([], False)
