"""Normalize legacy bodyweight targets and retain manual starting-load fallbacks."""

from dataclasses import replace
from math import isfinite

from metrics.plan_adherence import compatible_set
from metrics.set_interpretation import interpret_sets
from models.progression import SetGoal

HISTORY_START_REASONS = frozenset(
    {
        "no_history",
        "no_normal_baseline",
        "manual_start",
        "changed_set_count",
        "history_gap",
        "incomplete_sets",
        "missing_rir",
    }
)


def _working_settings(record, planned, *, legacy_bodyweight):
    ordered = sorted(record["sets"], key=lambda item: item.set_number)
    interpreted = tuple(zip(ordered, interpret_sets(ordered)))
    working = [
        item
        for item, meaning in interpreted
        if meaning.kind in ("working", "timed") and compatible_set(item, planned.target_unit)
    ]
    # Missing effort does not erase a recorded load. It cannot confirm increases.
    if not working:
        working = [
            item
            for item, meaning in interpreted
            if meaning.kind == "unknown" and compatible_set(item, planned.target_unit)
        ]
    if not working:
        return ()
    if any(
        not isfinite(item.weight)
        or item.weight < 0
        or (legacy_bodyweight and item.load is None and item.weight != 0)
        or (
            item.load is not None
            and item.load.load_type == "assisted_bodyweight"
            and item.load.assistance_kg is None
        )
        for item in working
    ):
        return ()
    kinds = {item.load.load_type if item.load else "legacy" for item in working}
    return tuple(working) if len(kinds) == 1 else ()


def with_history_starting_loads(
    result,
    upcoming,
    history,
    *,
    as_of,
    manual_load_exercise_ids=frozenset(),
    legacy_body_mass_exercise_ids=frozenset(),
    max_history_gap_days=21,
):
    """Fill starting targets from the latest ordinary exact-ID entry.

    Dates, plan IDs and target changes do not prevent reading past loads. These
    suggestions never enter comparison history or manufacture logged sets.
    """
    if result.block.phase not in ("normal", "unconfigured"):
        return result
    prescriptions = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    output = []
    for item in result.exercises:
        confirmed_body_mass = item.actual_exercise_id in legacy_body_mass_exercise_ids
        manual_bodyweight = item.actual_exercise_id in manual_load_exercise_ids
        legacy_zero = False
        if (
            not confirmed_body_mass
            and manual_bodyweight
            and any(g.load_type == "manual_bodyweight" for g in item.goals)
            and any(
                s.load is None and s.weight != 0
                for r in history.get(item.actual_exercise_id, ())
                if r["session_id"] in item.evidence_session_ids
                for s in r["sets"]
                if s.is_warmup is not True
            )
        ):
            item = replace(
                item,
                action="insufficient_data",
                goals=(),
                reason_code="manual_start",
                reason="Confirm the meaning of recorded bodyweight kilograms or choose added load manually.",
            )
        if not confirmed_body_mass and any(g.load_type == "manual_bodyweight" for g in item.goals):
            for record in history.get(item.actual_exercise_id, ()):
                if record["date"] > as_of or record["session_id"] not in item.evidence_session_ids:
                    continue
                sets = _working_settings(
                    record, prescriptions[item.plan_exercise_id], legacy_bodyweight=True
                )
                if sets and all(s.load is None and s.weight == 0 for s in sets):
                    legacy_zero = True
                    break
        if (confirmed_body_mass or legacy_zero) and any(
            g.load_type == "manual_bodyweight" for g in item.goals
        ):
            item = replace(
                item,
                goals=tuple(
                    replace(g, weight=0.0, load_type="bodyweight", assistance_kg=0.0)
                    if g.load_type == "manual_bodyweight"
                    else g
                    for g in item.goals
                ),
                notices=(
                    *item.notices,
                    "Additional load is 0 kg; future body mass is not assumed.",
                ),
            )
        if item.reason_code not in HISTORY_START_REASONS or item.goals:
            output.append(item)
            continue
        planned = prescriptions[item.plan_exercise_id]
        source, sets = None, ()
        records = [r for r in history.get(item.actual_exercise_id, ()) if r["date"] <= as_of]
        if records and sum(r["session_id"] == records[0]["session_id"] for r in records) > 1:
            output.append(item)
            continue
        if records:
            record = records[0]
            sets = _working_settings(
                record, planned, legacy_bodyweight=manual_bodyweight and not confirmed_body_mass
            )
            if sets:
                source = record
            # An incomplete or unusable latest entry must remain visible;
            # silently falling back to an older success hides missing evidence.
        if source is None:
            output.append(item)
            continue
        # Preserve back-off loads. A later heavier trial never raises the start.
        external = not (
            (confirmed_body_mass or manual_bodyweight) and any(s.load is None for s in sets)
        ) and all(s.load is None or s.load.load_type == "external" for s in sets)
        anchor = sets[0].weight
        goals = []
        for index in range(planned.set_count):
            if index >= len(sets):
                goals.append(
                    SetGoal(None, planned.target_min, planned.target_max, planned.target_unit)
                )
                continue
            recorded = sets[index]
            quantity = (
                recorded.duration_seconds
                if planned.target_unit == "seconds"
                else recorded.repetitions
            )
            exact = (
                index < len(sets)
                and quantity is not None
                and (planned.target_min <= quantity <= planned.target_max)
                and not (external and recorded.weight > anchor)
            )
            minimum = int(quantity) if exact else planned.target_min
            maximum = minimum if exact else planned.target_max
            if recorded.load is None and (
                confirmed_body_mass or (manual_bodyweight and recorded.weight == 0)
            ):
                goals.append(
                    SetGoal(
                        0.0,
                        minimum,
                        maximum,
                        planned.target_unit,
                        load_type="bodyweight",
                        assistance_kg=0.0,
                    )
                )
                continue
            goals.append(
                SetGoal(
                    min(recorded.weight, anchor) if external else recorded.weight,
                    minimum,
                    maximum,
                    planned.target_unit,
                    load_type=recorded.load.load_type if recorded.load else "legacy",
                    assistance_kg=recorded.load.assistance_kg if recorded.load else None,
                )
            )
        notices = list(item.notices)
        if confirmed_body_mass and any(s.load is None for s in sets):
            notices.append(
                "Legacy kilograms were confirmed as body mass only: additional load is 0 kg."
            )
        if len(sets) != planned.set_count:
            notices.append(
                f"History contains {len(sets)} working sets; this plan prescribes {planned.set_count}. "
                "Use the recorded sets in order; additional planned sets require choosing a working load."
            )
        if external and any(s.weight > anchor for s in sets[1:]):
            notices.append(
                "Later heavier trials are capped at the first recorded working load for this start."
            )
        if (item.scheduled_date - source["date"]).days > max_history_gap_days:
            notices.append(
                "This starting load comes from older history. Verify it during training before progressing."
            )
        if any(s.rir is None for s in sets) and planned.target_unit == "reps":
            notices.append(
                "Source RIR is incomplete. These recorded loads do not confirm an automatic increase."
            )
        notices.append(
            f"Source entry #{source['workout_exercise_id']}; recorded results remain unchanged."
        )
        output.append(
            replace(
                item,
                action="maintain",
                goals=tuple(goals),
                reason_code="reuse_exercise_baseline",
                reason="Repeat compatible recorded results using the current plan's reserve; establish targets only for new or changed sets.",
                evidence_session_ids=(source["session_id"],),
                evidence_dates=(source["date"],),
                evidence_workouts=(source["workout"] or "Recorded workout (not linked to a plan)",),
                notices=tuple(notices),
            )
        )
    return replace(result, exercises=tuple(output))
