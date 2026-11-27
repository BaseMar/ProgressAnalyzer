"""Choose recorded evidence separately from strict progression comparisons."""

from collections import Counter
from dataclasses import replace
from datetime import date, time

from metrics.plan_adherence import compatible_set
from metrics.plan_performance import _target_result, comparison_context, compute_plan_performance
from metrics.set_interpretation import interpret_sets
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
    Such rows can supply exercise progression evidence; they never establish
    plan coverage or replacements for the historical workout.
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
    """Use the latest exact exercise, independently of workout names or order.

    Unit, set count and prescription still constrain progression. Ambiguous
    repeated positions require an exact match instead of pooling their sets.
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
    if not candidates:
        return [], False
    latest = candidates[-1]
    same_session = [r for r in candidates if r["session_id"] == latest["session_id"]]
    if len(same_session) > 1:
        exact = [r for r in same_session if r["context"] == context]
        latest = exact[0] if len(exact) == 1 else {**latest, "ambiguous_recorded_exercises": True}
        return [latest], False
    # Confirmations cannot cross a prescription change, but moving an exercise
    # between workouts or plans does not reset an otherwise compatible result.
    history = []
    occurrences = Counter(row["session_id"] for row in candidates)
    for row in reversed(candidates):
        if row["context"][6:] != latest["context"][6:] or occurrences[row["session_id"]] > 1:
            break
        history.append(row)
    return list(reversed(history)), latest["context"][7:] != context[7:]


def exercise_history_observations(history, performances, planned, actual_id, context, *, workouts):
    """Combine exact-exercise records with omissions observed in linked plan coverage."""
    linked = {}
    for row in performances:
        if row["actual_exercise_id"] == actual_id:
            linked.setdefault(row["session_id"], []).append(row)
    output = []
    records = history.get(actual_id, ())
    occurrences = Counter(r["session_id"] for r in records)
    for record in reversed(records):
        previous = linked.get(record["session_id"], ())
        if occurrences[record["session_id"]] > 1 and previous:
            # Explicitly matched repeated positions retain their identity.
            if not any(r["session_id"] == record["session_id"] for r in output):
                output.extend(previous)
            continue
        ordered = sorted(record["sets"], key=lambda item: item.set_number)
        meanings = interpret_sets(ordered)
        selected = [
            (item, meaning)
            for item, meaning in zip(ordered, meanings)
            if meaning.counts_for_plan and compatible_set(item, planned.target_unit)
        ]
        source = (
            previous[0]
            if len(previous) == 1 and previous[0]["unit"] == planned.target_unit
            else None
        )
        source_context = source["context"] if source else context
        prescription = record.get("prescription")
        if source is None and prescription and prescription["target_unit"] == planned.target_unit:
            source_context = (
                *context[:7],
                prescription["set_count"],
                prescription["target_min"],
                prescription["target_max"],
                prescription["target_rir"],
            )
        expected = replace(planned, set_count=source_context[7])
        selected = selected[: expected.set_count]
        sets, interpretations = zip(*selected) if selected else ((), ())
        output.append(
            {
                "context": source_context,
                "day_id": source["day_id"] if source else -record["workout_exercise_id"],
                "session_id": record["session_id"],
                "performed_on": record["date"],
                "start_time": record.get("start_time"),
                "scheduled_date": source["scheduled_date"] if source else record["date"],
                "workout": record["workout"] or "Recorded workout (not linked to a plan)",
                "actual_exercise_id": actual_id,
                "unit": planned.target_unit,
                "excluded_set_kinds": tuple(m.kind for m in meanings if not m.counts_for_plan),
                "ambiguous_recorded_exercises": occurrences[record["session_id"]] > 1,
                **_target_result(sets, expected, interpretations),
            }
        )
    omissions = [
        row
        for session_id, rows in linked.items()
        if session_id is not None and session_id not in occurrences
        for row in rows
        if row["performed_on"] is not None
        and row["unit"] == planned.target_unit
        and not row["sets"]
    ]
    if not omissions:
        return output
    linked_start_times = {
        workout.slot.session_id: workout.slot.performed_start_time for workout in workouts
    }

    def performed_order(row):
        start = row.get("start_time", linked_start_times.get(row["session_id"]))
        return row["performed_on"], start is not None, start or time.min, row["session_id"]

    return sorted([*output, *omissions], key=performed_order)
