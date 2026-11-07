"""Deterministic progression, calendar deloads and post-deload return targets."""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from math import isclose, isfinite

from metrics.plan_performance import comparison_context, compute_plan_performance
from metrics.load_metrics import recorded_load, same_loads
from metrics.recommendation_history import recommendation_history, with_recorded_baselines
from metrics.training_block import deload_exercise_target, is_deload_workout, training_block_phase
from models.plan_adherence import PlanAdherenceInput, PlannedWorkout
from models.progression import DeloadPolicy, ExerciseRecommendation, ProgressionPolicy, SetGoal, WorkoutRecommendation


def _evidence_problem(latest, planned, scheduled_date, policy):
    sets = latest["sets"]
    if (scheduled_date - latest["performed_on"]).days > policy.max_history_gap_days:
        return "history_gap", "The latest execution is outside the policy's history-gap limit."
    if latest["missing_sets"] or not sets:
        excluded = latest.get("excluded_set_kinds", ())
        if "invalid" in excluded:
            return "invalid_values", "Review invalid recorded loads or RIR values in the latest execution."
        if "light" in excluded:
            return "light_sets", "The latest execution contains light RIR 4–5 sets instead of every planned ordinary working set."
        if "low_effort" in excluded:
            return "low_effort_sets", "The latest execution contains RIR above 5; these sets stay in history but do not support ordinary progression."
        return "incomplete_sets", "The latest linked session does not contain every planned set."
    if any(not isfinite(item["weight"]) or item["weight"] < 0 for item in sets):
        return "invalid_values", "Recorded loads are invalid."
    if any(recorded_load(item) is None for item in sets):
        return "unknown_load", "Complete the body-mass or assistance snapshot before comparing loads."
    if len({item.get("load_type", "legacy") for item in sets}) > 1:
        return "mixed_load_convention", "The latest sets use different load conventions; select the next load manually."
    if any(item.get("load_type") in ("bodyweight", "assisted_bodyweight") for item in sets):
        return "bodyweight_load_manual", "Select additional weight or assistance manually using total load. A future body mass is not assumed; reducing assistance increases difficulty."
    if planned.target_unit == "seconds":
        return None
    if planned.target_rir is None:
        return "missing_target_rir", "Set a target RIR before generating progression goals."
    if any(item["rir"] is None for item in sets):
        return "missing_rir", "The latest execution has missing RIR data; missing is not zero."
    if any(not isfinite(item["weight"]) or item["weight"] < 0
           or not isfinite(item["rir"]) or item["rir"] < 0 for item in sets):
        return "invalid_values", "Recorded loads or RIR values are invalid."
    return None


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
    Complete working sets with RIR support increases within an unchanged context.
    Changed prescriptions and other workouts may supply starting loads only.
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
        observed = with_recorded_baselines(data, performances, planned, actual_id, as_of=as_of)
        history, baseline_only = recommendation_history(observed, context,
            as_of=as_of, block_start=block_start)
        def decision(action, code, reason, goals=(), evidence=()):
            return ExerciseRecommendation(
                target.plan_exercise_id, planned.exercise_id, actual_id, upcoming.slot.scheduled_date,
                action, tuple(goals), planned.target_rir if planned.target_unit == "reps" else None, code, reason,
                tuple(row["session_id"] for row in evidence), tuple(row["performed_on"] for row in evidence),
                tuple(row["workout"] for row in evidence),
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
        problem = _evidence_problem(latest, planned, upcoming.slot.scheduled_date, policy)
        if problem:
            output.append(decision("insufficient_data", *problem, evidence=evidence))
            continue
        if baseline_only and len(sets) != planned.set_count:
            output.append(decision("insufficient_data", "changed_set_count",
                "This exercise has recorded history, but the new set count differs. Choose starting loads for the new sets manually.", evidence=evidence))
            continue
        hold = tuple(SetGoal(item["weight"], planned.target_min, planned.target_max, planned.target_unit) for item in sets)
        if baseline_only:
            output.append(decision("maintain", "reuse_exercise_baseline",
                "Use the recorded loads as starting points for the current range and RIR. "
                "The workout, exercise order or prescription changed; adjust loads as needed to meet the new targets. "
                "Record this context before an automatic increase; older executions do not count as confirmations.", hold, evidence))
            continue
        if planned.target_unit == "seconds":
            output.append(decision("maintain", "timed_exercise", "Keep the recorded loads and time range; timed work does not require repetition-based RIR and automatic timed progression is not supported.", hold, evidence))
            continue
        if any(item["rir"] < planned.target_rir for item in sets):
            output.append(decision("maintain", "rir_below_target", "Keep the logged loads and planned range: at least one set had less reserve than the target.", hold, evidence))
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
            qualifies = qualifies and same_loads(row["sets"], sets)
            qualifies = qualifies and not row["missing_sets"] and len(row["sets"]) == planned.set_count
            qualifies = qualifies and all(item["progression_eligible"] and item["rir"] is not None
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


def _reduced_load(weight, step, policy):
    """Subtract whole hardware steps from the logged load, never invent a step."""
    if weight <= 0:
        return None
    load, increment = Decimal(str(weight)), Decimal(str(step))
    steps = (load * Decimal(str(policy.load_reduction)) / increment).to_integral_value(rounding=ROUND_CEILING)
    reduction = steps * increment
    if reduction / load > Decimal(str(policy.max_load_reduction)) or reduction >= load:
        return None
    return float(load - reduction)


def recommend_workout(
    data: PlanAdherenceInput, upcoming: PlannedWorkout, *, as_of: date, settings,
    policy: ProgressionPolicy = ProgressionPolicy(), deload_policy: DeloadPolicy = DeloadPolicy(),
    substitutions=None, replacement_weight_steps=None, settings_by_version=None,
) -> WorkoutRecommendation:
    """General entry point: ordinary progression, deload or return baseline.

    Configured blocks repeat from their anchor. Deload executions never establish
    ordinary baselines/confirmations. The first ordinary exposure in a new cycle
    may reuse the last normal load from the preceding cycle, without increasing it.
    Historical versions use their own settings when a mapping is supplied.
    """
    phase = training_block_phase(upcoming.slot.scheduled_date, settings)
    version_settings = settings_by_version if settings_by_version is not None else {
        item.slot.version_id: settings for item in data.workouts}
    # Initial block setup may cover workouts linked to an earlier, unconfigured
    # version. Interpret those dates with the selected block, without changing
    # historical snapshots. Explicitly different settings still reset history.
    version_settings = {version_id: configured if configured is not None else settings
                        for version_id, configured in version_settings.items()}
    # A manual change of anchor/length starts a fresh history. Revisions with the
    # same block settings preserve it. Both scheduled and actual dates matter.
    ordinary = replace(data, workouts=tuple(item for item in data.workouts
        if settings is not None and version_settings.get(item.slot.version_id) == settings
        and item.slot.scheduled_date >= settings.block_start
        and item.slot.performed_on is not None and item.slot.performed_on >= settings.block_start
        and not is_deload_workout(item.slot, settings)))
    current = replace(ordinary, workouts=tuple(item for item in ordinary.workouts
        if phase.cycle_start is not None and item.slot.scheduled_date >= phase.cycle_start))
    results = recommend_normal_workout(current, upcoming, as_of=as_of,
        block_start=phase.cycle_start if phase.cycle_start else settings.block_start if settings else None,
        policy=policy, substitutions=substitutions, replacement_weight_steps=replacement_weight_steps)
    if phase.phase in ("unconfigured", "not_started") or upcoming.slot.session_id is not None:
        return WorkoutRecommendation(phase, results)
    performances = compute_plan_performance(ordinary, as_of=as_of)
    output = []
    for position, (target, result) in enumerate(zip(upcoming.targets, results), start=1):
        planned = target.exercise
        if phase.phase == "normal" and result.reason_code != "no_history":
            output.append(result)
            continue
        context = comparison_context(upcoming.slot, position, planned, result.actual_exercise_id)
        observed = with_recorded_baselines(ordinary, performances, planned, result.actual_exercise_id, as_of=as_of)
        candidates = [row for row in observed
                      if row["performed_on"] is not None and row["performed_on"] <= as_of]
        if phase.phase == "deload":
            candidates = [row for row in candidates if row["scheduled_date"] >= phase.cycle_start
                       and row["performed_on"] >= phase.cycle_start
                       and row["scheduled_date"] < phase.deload_start and row["performed_on"] < phase.deload_start]
        else:
            # Only the immediately preceding cycle may supply the return load.
            previous_start = phase.cycle_start - timedelta(weeks=settings.block_weeks)
            candidates = [row for row in candidates if previous_start <= row["scheduled_date"] < phase.cycle_start
                       and previous_start <= row["performed_on"] < phase.cycle_start]
        history, _ = recommendation_history(candidates, context, as_of=as_of, block_start=None)
        if not history:
            output.append(replace(result, action="insufficient_data", goals=(), reason_code="no_normal_baseline",
                                  reason="No linked ordinary execution in the relevant cycle; deload results are not used as a baseline."))
            continue
        latest = history[-1]
        result = replace(result, evidence_session_ids=(latest["session_id"],), evidence_dates=(latest["performed_on"],),
                         evidence_workouts=(latest["workout"],))
        problem = _evidence_problem(latest, planned, upcoming.slot.scheduled_date, policy)
        if problem:
            output.append(replace(result, action="insufficient_data", goals=(), reason_code=problem[0], reason=problem[1]))
            continue
        if len(latest["sets"]) != planned.set_count:
            output.append(replace(result, action="insufficient_data", goals=(), reason_code="changed_set_count",
                                  reason="The recorded set count differs from the current prescription; select starting loads manually."))
            continue
        if phase.phase == "normal":
            goals = tuple(SetGoal(item["weight"], planned.target_min, planned.target_max, planned.target_unit) for item in latest["sets"])
            output.append(replace(result, action="maintain", goals=goals, reason_code="resume_after_deload",
                                  reason="Resume the last ordinary loads and planned range without an increase. New-cycle executions must establish progression again."))
            continue
        if planned.target_unit != "reps":
            output.append(replace(result, action="insufficient_data", goals=(), reason_code="deload_timed_not_supported",
                                  reason="This date is deload, but automatic targets for timed exercises are not supported."))
            continue
        step = planned.weight_increment if result.actual_exercise_id == planned.exercise_id else (replacement_weight_steps or {}).get(result.actual_exercise_id)
        if step is None or isinstance(step, bool) or not isinstance(step, (int, float)) or not isfinite(step) or step <= 0:
            output.append(replace(result, action="insufficient_data", goals=(), reason_code="missing_weight_step" if step is None else "invalid_weight_step",
                                  reason="Deload needs the actual exercise's available positive weight step; the original exercise's step is not reused for a substitute."))
            continue
        reduced = deload_exercise_target(planned, deload_policy)
        weights = [_reduced_load(item["weight"], step, deload_policy) for item in latest["sets"][:reduced.set_count]]
        if any(weight is None for weight in weights):
            output.append(replace(result, action="insufficient_data", goals=(), reason_code="deload_load_not_supported",
                                  reason="No supported reduced positive load within the deload policy limit. Zero-load/bodyweight and assistance require manual load selection."))
            continue
        goals = tuple(SetGoal(weight, reduced.target_min, reduced.target_max, "reps") for weight in weights)
        output.append(replace(result, action="deload", goals=goals, target_rir=reduced.target_rir,
                              reason_code="scheduled_deload", reason="Scheduled deload: fewer working sets (rounded up, at least one), lower-bound reps, reduced loads in whole equipment steps and more reserve."))
    return WorkoutRecommendation(phase, tuple(output))
