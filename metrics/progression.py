"""Deterministic double progression for NORMAL sessions only.

Deload classification/adjustments belong to the next stage. This engine returns
derived targets, never writes them into a plan, and does not guarantee outcomes.
"""
from datetime import date
from decimal import Decimal
from math import isclose, isfinite

from metrics.plan_performance import comparison_context, compute_plan_performance
from models.plan_adherence import PlanAdherenceInput, PlannedWorkout
from models.progression import ExerciseRecommendation, ProgressionPolicy, SetGoal


def recommend_normal_workout(
    data: PlanAdherenceInput, upcoming: PlannedWorkout, *, as_of: date,
    block_start: date | None,
    policy: ProgressionPolicy = ProgressionPolicy(),
    substitutions: dict[int, int] | None = None,
    replacement_weight_steps: dict[int, float] | None = None,
) -> tuple[ExerciseRecommendation, ...]:
    """Recommend per planned position, using only past evidence in this block.

    Substitutions are explicit choices for the upcoming workout, keyed by plan
    position ID. They are not silently carried forward from a past approval.
    Only comparable, explicitly working sets with complete RIR support increases.
    The RIR target acts as a minimum reserve, not a requirement to reach failure.
    """
    if type(as_of) is not date or type(upcoming.slot.scheduled_date) is not date:
        raise ValueError("Recommendation dates must be dates")
    if upcoming.slot.scheduled_date < as_of:
        raise ValueError("Cannot recommend a next workout in the past")
    if block_start is not None and type(block_start) is not date:
        raise ValueError("Block start must be a date or None")
    substitutions = substitutions or {}
    replacement_weight_steps = replacement_weight_steps or {}
    target_ids = {target.plan_exercise_id for target in upcoming.targets}
    if not set(substitutions).issubset(target_ids) or any(type(value) is not int or value < 1 for value in substitutions.values()):
        raise ValueError("Substitutions must identify positions in the upcoming workout and valid exercise IDs")
    performances = compute_plan_performance(data, as_of=as_of)
    output = []
    for position, target in enumerate(upcoming.targets, start=1):
        planned = target.exercise
        actual_id = substitutions.get(target.plan_exercise_id, planned.exercise_id)
        context = comparison_context(upcoming.slot, position, planned, actual_id)
        history = [row for row in performances if row["context"] == context
                   and row["session_id"] is not None and row["performed_on"] is not None
                   and row["performed_on"] <= as_of
                   and (block_start is None or row["performed_on"] >= block_start)]
        def decision(action, code, reason, goals=(), evidence=()):
            return ExerciseRecommendation(
                target.plan_exercise_id, planned.exercise_id, actual_id, upcoming.slot.scheduled_date,
                action, tuple(goals), planned.target_rir, code, reason,
                tuple(row["session_id"] for row in evidence), tuple(row["performed_on"] for row in evidence),
            )
        if block_start is None:
            output.append(decision("insufficient_data", "block_not_configured", "Configure the training block before generating goals."))
            continue
        if upcoming.slot.scheduled_date < block_start:
            output.append(decision("insufficient_data", "before_block", "The configured training block has not started for this date."))
            continue
        if upcoming.slot.session_id is not None:
            output.append(decision("insufficient_data", "already_recorded", "This planned workout already has a recorded session."))
            continue
        if not history:
            output.append(decision("insufficient_data", "no_history", "No linked execution of this exercise in the same workout context and block."))
            continue
        latest = history[-1]
        evidence = (latest,)
        sets = latest["sets"]
        if (upcoming.slot.scheduled_date - latest["performed_on"]).days > policy.max_history_gap_days:
            output.append(decision("insufficient_data", "history_gap", "The latest execution is outside the policy's history-gap limit.", evidence=evidence))
            continue
        if latest["missing_sets"] or not sets:
            output.append(decision("insufficient_data", "incomplete_sets", "The latest linked session does not contain every planned set.", evidence=evidence))
            continue
        if any(item["is_warmup"] is not False for item in sets):
            output.append(decision("insufficient_data", "unknown_set_type", "Mark the credited sets as working sets before using them for progression.", evidence=evidence))
            continue
        if planned.target_rir is None:
            output.append(decision("insufficient_data", "missing_target_rir", "Set a target RIR before generating progression goals.", evidence=evidence))
            continue
        if any(item["rir"] is None for item in sets):
            output.append(decision("insufficient_data", "missing_rir", "The latest execution has missing RIR data; missing is not zero.", evidence=evidence))
            continue
        if any(not isfinite(item["weight"]) or item["weight"] < 0
               or not isfinite(item["rir"]) or item["rir"] < 0 for item in sets):
            output.append(decision("insufficient_data", "invalid_values", "Recorded loads or RIR values are invalid.", evidence=evidence))
            continue
        hold = tuple(SetGoal(item["weight"], planned.target_min, planned.target_max, planned.target_unit) for item in sets)
        if any(item["rir"] < planned.target_rir for item in sets):
            output.append(decision("maintain", "rir_below_target", "Keep the logged loads and planned range: at least one set had less reserve than the target.", hold, evidence))
            continue
        if planned.target_unit == "seconds":
            output.append(decision("maintain", "timed_exercise", "Keep the recorded loads and time range; this stage does not prescribe timed progression.", hold, evidence))
            continue
        if any(item["reps"] < planned.target_min for item in sets):
            output.append(decision("maintain", "below_range", "Keep the loads and planned range; not every set reached the lower repetition bound.", hold, evidence))
            continue
        weight = sets[0]["weight"]
        if any(not isclose(item["weight"], weight, rel_tol=0, abs_tol=1e-6) for item in sets):
            output.append(decision("maintain", "mixed_loads", "Keep the per-set loads: automatic progression currently requires one working load.", hold, evidence))
            continue
        if any(item["reps"] > planned.target_max for item in sets) and any(item["reps"] < planned.target_max for item in sets):
            output.append(decision("maintain", "mixed_range", "Some sets exceeded the range while others remain below its upper bound; keep the planned range before increasing the goal.", hold, evidence))
            continue
        reps = [min(item["reps"], planned.target_max) for item in sets]
        if any(value < planned.target_max for value in reps):
            index = min(range(len(reps)), key=lambda index: (reps[index], index))
            reps[index] += 1
            goals = tuple(SetGoal(weight, value, value, "reps") for value in reps)
            output.append(decision("increase_reps", "one_more_rep", "Add one total repetition to the lowest-repetition set, keeping load and target RIR.", goals, evidence))
            continue
        confirmed = history[-policy.confirmations_required:]
        qualifies = len(confirmed) == policy.confirmations_required
        qualifies = qualifies and len({row["session_id"] for row in confirmed}) == policy.confirmations_required
        qualifies = qualifies and len({row["performed_on"] for row in confirmed}) == policy.confirmations_required
        for row in confirmed:
            qualifies = qualifies and not row["missing_sets"] and len(row["sets"]) == planned.set_count
            qualifies = qualifies and all(item["is_warmup"] is False and item["rir"] is not None
                and isfinite(item["rir"]) and item["rir"] >= planned.target_rir
                and item["reps"] >= planned.target_max
                and isclose(item["weight"], weight, rel_tol=0, abs_tol=1e-6) for item in row["sets"])
        qualifies = qualifies and all((new["performed_on"] - old["performed_on"]).days <= policy.max_history_gap_days
                                      for old, new in zip(confirmed, confirmed[1:]))
        ceiling = tuple(SetGoal(weight, planned.target_max, planned.target_max, "reps") for _ in sets)
        if not qualifies:
            output.append(decision("maintain", "confirm_upper_range", "Repeat the upper-range result at this load and target RIR before increasing weight.", ceiling, evidence))
            continue
        if weight <= 0:
            output.append(decision("maintain", "zero_load", "Keep the upper-range goal; this engine does not infer how to add load to a zero-load or bodyweight exercise.", ceiling, confirmed))
            continue
        step = planned.weight_increment if actual_id == planned.exercise_id else replacement_weight_steps.get(actual_id)
        if step is None:
            output.append(decision("insufficient_data", "missing_weight_step", "Set the available weight step for the actual exercise; another exercise's step is not reused.", evidence=confirmed))
            continue
        if isinstance(step, bool) or not isinstance(step, (int, float)) or not isfinite(step) or step <= 0:
            output.append(decision("insufficient_data", "invalid_weight_step", "The actual exercise's weight step must be finite and positive.", evidence=confirmed))
            continue
        if step / weight > policy.max_relative_weight_increase:
            output.append(decision("maintain", "weight_step_not_supported", "Keep the upper-range goal: this weight step exceeds the policy's relative increase limit.", ceiling, confirmed))
            continue
        next_weight = float(Decimal(str(weight)) + Decimal(str(step)))
        goals = tuple(SetGoal(next_weight, planned.target_min, planned.target_min, "reps") for _ in sets)
        output.append(decision("increase_weight", "upper_range_confirmed", "The required consecutive executions reached the upper bound with enough reserve; add one available weight step and target the lower bound.", goals, confirmed))
    return tuple(output)
