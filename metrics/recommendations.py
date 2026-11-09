"""Versioned recommendation service: evidence, ordinary decisions and deloads."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal
from math import isfinite

from metrics.load_metrics import recorded_load, same_loads
from metrics.plan_performance import comparison_context, compute_plan_performance
from metrics.progression_rules import session_decision, set_goal, weight_step_problem
from metrics.recommendation_history import (
    changed_context_reason,
    recommendation_history,
    with_recorded_baselines,
)
from metrics.training_block import deload_exercise_target, is_deload_workout, training_block_phase
from models.progression import (
    DeloadPolicy,
    ExerciseRecommendation,
    ProgressionPolicy,
    WorkoutRecommendation,
)


def _evidence_problem(latest, planned, scheduled_date, policy):
    sets = latest["sets"]
    if (scheduled_date - latest["performed_on"]).days > policy.max_history_gap_days:
        return (
            "history_gap",
            "More than 21 days since the last execution. Review the history and choose a new working start manually.",
        )
    if latest["missing_sets"] or not sets:
        excluded = latest.get("excluded_set_kinds", ())
        if "invalid" in excluded:
            return (
                "invalid_values",
                "Review invalid recorded loads or RIR values in the latest execution.",
            )
        if "light" in excluded:
            return (
                "light_sets",
                "The latest execution has inferred light sets instead of all planned working sets. Review their purpose in History.",
            )
        if "low_effort" in excluded:
            return (
                "low_effort_sets",
                "The latest execution has inferred low-effort sets. Review their purpose in History; explicit working labels take precedence.",
            )
        return (
            "incomplete_sets",
            "The latest linked session does not contain every planned working set.",
        )
    if latest.get("ambiguous_recorded_exercises"):
        return (
            "ambiguous_recorded_exercises",
            "Multiple recorded exercises match one planned position. Confirm the intended exercise in History before increasing the target.",
        )
    if any(not isfinite(item["weight"]) or item["weight"] < 0 for item in sets):
        return "invalid_values", "Recorded loads are invalid."
    if any(recorded_load(item) is None for item in sets):
        return (
            "unknown_load",
            "Complete the body-mass or assistance snapshot before comparing loads.",
        )
    if len({item.get("load_type", "legacy") for item in sets}) > 1:
        return (
            "mixed_load_convention",
            "Load conventions differ between sets; select the working settings manually.",
        )
    if planned.target_unit == "seconds":
        return None
    if planned.target_rir is None:
        return "missing_target_rir", "Set a target RIR before generating progression goals."
    if any(item["rir"] is None for item in sets):
        return "missing_rir", "The latest execution has missing RIR data; missing is not zero."
    if any(not isfinite(item["rir"]) or item["rir"] < 0 for item in sets):
        return "invalid_values", "Recorded RIR values are invalid."
    return None


def _plateau_history(history, planned, policy):
    if planned.target_unit != "reps" or len(history) < policy.plateau_exposures:
        return ()
    rows = history[-policy.plateau_exposures :]
    if len({row["performed_on"] for row in rows}) != len(rows):
        return ()
    for row in rows:
        if (
            row["missing_sets"]
            or len(row["sets"]) != planned.set_count
            or not row["progression_eligible"]
        ):
            return ()
        if not same_loads(rows[-1]["sets"], row["sets"]):
            return ()
        if any(item["rir"] is None or item["rir"] < planned.target_rir for item in row["sets"]):
            return ()
    if any(
        (b["performed_on"] - a["performed_on"]).days > policy.max_history_gap_days
        for a, b in zip(rows, rows[1:])
    ):
        return ()
    totals = [sum(s["reps"] for s in row["sets"]) for row in rows]
    if any(b > a for a, b in zip(totals, totals[1:])) or all(
        s["reps"] >= planned.target_max for s in rows[-1]["sets"]
    ):
        return ()
    base = rows[0]["sets"]
    previous_improved = False
    for row in rows[1:]:
        improved = all(
            s["reps"] == old["reps"] and s["rir"] >= old["rir"] for s, old in zip(row["sets"], base)
        ) and any(s["rir"] > old["rir"] for s, old in zip(row["sets"], base))
        if improved and previous_improved:
            return ()
        previous_improved = improved
    return rows


def recommend_normal_workout(
    data,
    upcoming,
    *,
    as_of,
    block_start=None,
    policy=ProgressionPolicy(),
    substitutions=None,
    replacement_weight_steps=None,
):
    if type(as_of) is not date or type(upcoming.slot.scheduled_date) is not date:
        raise ValueError("Recommendation dates must be dates")
    if upcoming.slot.scheduled_date < as_of:
        raise ValueError("Cannot recommend a next workout in the past")
    if block_start is not None and type(block_start) is not date:
        raise ValueError("Block start must be a date or None")
    substitutions, replacement_weight_steps = substitutions or {}, replacement_weight_steps or {}
    target_ids = {target.plan_exercise_id for target in upcoming.targets}
    if not set(substitutions).issubset(target_ids) or any(
        type(value) is not int or value < 1 for value in substitutions.values()
    ):
        raise ValueError(
            "Substitutions must identify positions in the upcoming workout and valid exercise IDs"
        )
    performances = compute_plan_performance(data, as_of=as_of)
    output = []
    for position, target in enumerate(upcoming.targets, start=1):
        planned = target.exercise
        actual_id = substitutions.get(target.plan_exercise_id, planned.exercise_id)
        context = comparison_context(upcoming.slot, position, planned, actual_id)
        observed = with_recorded_baselines(data, performances, planned, actual_id, as_of=as_of)
        history, baseline_only = recommendation_history(
            observed, context, as_of=as_of, block_start=block_start
        )

        def decision(action, code, reason, goals=(), evidence=(), notices=()):
            return ExerciseRecommendation(
                target.plan_exercise_id,
                planned.exercise_id,
                actual_id,
                upcoming.slot.scheduled_date,
                action,
                tuple(goals),
                planned.target_rir if planned.target_unit == "reps" else None,
                code,
                reason,
                tuple(row["session_id"] for row in evidence),
                tuple(row["performed_on"] for row in evidence),
                tuple(row["workout"] for row in evidence),
                tuple(notices),
            )

        if upcoming.slot.session_id is not None:
            output.append(
                decision(
                    "insufficient_data",
                    "already_recorded",
                    "This workout already has a recorded session.",
                )
            )
            continue
        if block_start is not None and upcoming.slot.scheduled_date < block_start:
            output.append(
                decision(
                    "insufficient_data",
                    "before_block",
                    "The configured training block has not started for this date.",
                )
            )
            continue
        if not history:
            output.append(
                decision(
                    "insufficient_data",
                    "no_history",
                    "No established working start in this context. Review the history and choose the starting load manually.",
                )
            )
            continue
        latest, evidence = history[-1], (history[-1],)
        problem = _evidence_problem(latest, planned, upcoming.slot.scheduled_date, policy)
        if problem:
            output.append(decision("insufficient_data", *problem, evidence=evidence))
            continue
        if baseline_only:
            code = (
                "changed_set_count" if len(latest["sets"]) != planned.set_count else "manual_start"
            )
            output.append(
                decision(
                    "insufficient_data",
                    code,
                    changed_context_reason(latest, context, upcoming.slot.name),
                    evidence=evidence,
                )
            )
            continue
        step = (
            planned.weight_increment
            if actual_id == planned.exercise_id
            else replacement_weight_steps.get(actual_id)
        )
        manual_load = actual_id in data.manual_load_exercise_ids
        action, code, reason, goals = session_decision(
            planned, latest["sets"], step, policy, manual_load=manual_load
        )
        # The shipped policy uses one execution. Explicit custom policies remain auditable.
        if action in ("increase_weight", "equalize_weight") and policy.confirmations_required > 1:
            confirmed = history[-policy.confirmations_required :]
            qualifies = len(confirmed) == policy.confirmations_required and len(
                {r["performed_on"] for r in confirmed}
            ) == len(confirmed)
            qualifies = qualifies and all(
                not r["missing_sets"]
                and same_loads(r["sets"], latest["sets"])
                and all(
                    s["rir"] is not None
                    and s["rir"] >= planned.target_rir
                    and s["reps"] >= planned.target_max
                    for s in r["sets"]
                )
                for r in confirmed
            )
            qualifies = qualifies and all(
                (b["performed_on"] - a["performed_on"]).days <= policy.max_history_gap_days
                for a, b in zip(confirmed, confirmed[1:])
            )
            if not qualifies:
                action, code, reason = (
                    "maintain",
                    "confirm_upper_range",
                    "Repeat the ceiling for the explicitly configured confirmation count.",
                )
                goals = tuple(set_goal(s, planned.target_max) for s in latest["sets"])
            else:
                evidence = tuple(confirmed)
        notices = []
        if any(s.get("classification_source") in ("rir", "sequence") for s in latest["sets"]):
            notices.append(
                "Set purpose inferred from RIR and order; explicit corrections in History take precedence."
            )
        plateau = (
            ()
            if manual_load and any(s.get("load_type", "legacy") == "legacy" for s in latest["sets"])
            else _plateau_history(history, planned, policy)
        )
        if plateau:
            notices.append(
                "Possible plateau: four comparable executions without output or confirmed reserve improvement. Review rest, technique and recovery; sets are not added automatically."
            )
            evidence = tuple(plateau)
        output.append(decision(action, code, reason, goals, evidence, notices))
    return tuple(output)


def _reduced_load(weight, step, policy):
    if weight <= 0:
        return None
    load, increment = Decimal(str(weight)), Decimal(str(step))
    count = (load * Decimal(str(policy.load_reduction)) / increment).to_integral_value(
        rounding=ROUND_CEILING
    )
    reduction = count * increment
    if reduction / load > Decimal(str(policy.max_load_reduction)) or reduction >= load:
        return None
    return float(load - reduction)


def recommend_workout(
    data,
    upcoming,
    *,
    as_of,
    settings,
    policy=ProgressionPolicy(),
    deload_policy=DeloadPolicy(),
    substitutions=None,
    replacement_weight_steps=None,
    settings_by_version=None,
):
    phase = training_block_phase(upcoming.slot.scheduled_date, settings)
    configured = (
        settings_by_version
        if settings_by_version is not None
        else {w.slot.version_id: settings for w in data.workouts}
    )
    configured = {
        key: value if value is not None else settings for key, value in configured.items()
    }
    ordinary = replace(
        data,
        workouts=tuple(
            w
            for w in data.workouts
            if (settings is None or configured.get(w.slot.version_id) == settings)
            and (
                settings is None
                or (
                    w.slot.scheduled_date >= settings.block_start
                    and w.slot.performed_on is not None
                    and w.slot.performed_on >= settings.block_start
                )
            )
            and not is_deload_workout(w.slot, configured.get(w.slot.version_id))
        ),
    )
    current = replace(
        ordinary,
        workouts=tuple(
            w
            for w in ordinary.workouts
            if phase.cycle_start is None
            or (
                w.slot.scheduled_date >= phase.cycle_start
                and w.slot.performed_on is not None
                and w.slot.performed_on >= phase.cycle_start
            )
        ),
    )
    results = recommend_normal_workout(
        current,
        upcoming,
        as_of=as_of,
        block_start=phase.cycle_start or (settings.block_start if settings else None),
        policy=policy,
        substitutions=substitutions,
        replacement_weight_steps=replacement_weight_steps,
    )
    if phase.phase in ("unconfigured", "not_started") or upcoming.slot.session_id is not None:
        return WorkoutRecommendation(phase, results)
    performances = compute_plan_performance(ordinary, as_of=as_of)
    output = []
    for position, (target, result) in enumerate(zip(upcoming.targets, results), 1):
        if phase.phase == "normal" and result.reason_code != "no_history":
            output.append(result)
            continue
        planned = target.exercise
        context = comparison_context(upcoming.slot, position, planned, result.actual_exercise_id)
        observed = with_recorded_baselines(
            ordinary, performances, planned, result.actual_exercise_id, as_of=as_of
        )
        if phase.phase == "deload":
            candidates = [
                r
                for r in observed
                if r["performed_on"] is not None
                and phase.cycle_start <= r["scheduled_date"] < phase.deload_start
                and phase.cycle_start <= r["performed_on"] < phase.deload_start
                and r["performed_on"] <= as_of
            ]
        else:
            previous_start = phase.cycle_start - timedelta(weeks=settings.block_weeks)
            candidates = [
                r
                for r in observed
                if r["performed_on"] is not None
                and previous_start <= r["scheduled_date"] < phase.cycle_start
                and previous_start <= r["performed_on"] < phase.cycle_start
                and r["performed_on"] <= as_of
            ]
        history, baseline_only = recommendation_history(
            candidates, context, as_of=as_of, block_start=None
        )
        if not history:
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code="no_normal_baseline",
                    reason="No established ordinary execution in the relevant cycle. Choose the working start manually; deload results are not a baseline.",
                )
            )
            continue
        latest = history[-1]
        result = replace(
            result,
            evidence_session_ids=(latest["session_id"],),
            evidence_dates=(latest["performed_on"],),
            evidence_workouts=(latest["workout"],),
        )
        problem = _evidence_problem(latest, planned, upcoming.slot.scheduled_date, policy)
        if problem:
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code=problem[0],
                    reason=problem[1],
                )
            )
            continue
        if baseline_only or len(latest["sets"]) != planned.set_count:
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code="manual_start",
                    reason=changed_context_reason(latest, context, upcoming.slot.name),
                )
            )
            continue
        if phase.phase == "normal":
            goals = tuple(
                set_goal(s, planned.target_min, planned.target_max, unit=planned.target_unit)
                for s in latest["sets"]
            )
            output.append(
                replace(
                    result,
                    action="maintain",
                    goals=goals,
                    reason_code="resume_after_deload",
                    reason="Resume the last ordinary loads and range. The first exposure after deload verifies the baseline without an immediate increase.",
                )
            )
            continue
        if (
            planned.target_unit != "reps"
            or result.actual_exercise_id in data.manual_load_exercise_ids
            or any(
                s.get("load_type") in ("bodyweight", "assisted_bodyweight") for s in latest["sets"]
            )
        ):
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code="deload_timed_not_supported"
                    if planned.target_unit == "seconds"
                    else "deload_load_not_supported",
                    reason="Choose the lighter time/bodyweight/assistance setting manually for deload; ordinary progression is paused.",
                )
            )
            continue
        step = (
            planned.weight_increment
            if result.actual_exercise_id == planned.exercise_id
            else (replacement_weight_steps or {}).get(result.actual_exercise_id)
        )
        problem = weight_step_problem(step)
        if problem:
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code=problem[0],
                    reason=problem[1],
                )
            )
            continue
        reduced = deload_exercise_target(planned, deload_policy)
        source_sets = latest["sets"][: reduced.set_count]
        weights = [_reduced_load(s["weight"], step, deload_policy) for s in source_sets]
        if any(w is None for w in weights):
            output.append(
                replace(
                    result,
                    action="insufficient_data",
                    goals=(),
                    reason_code="deload_load_not_supported",
                    reason="No positive equipment setting gives the chosen 30–40% load reduction. Select the deload load manually.",
                )
            )
            continue
        goals = tuple(set_goal(s, s["reps"], weight=w) for s, w in zip(source_sets, weights))
        output.append(
            replace(
                result,
                action="deload",
                goals=goals,
                target_rir=reduced.target_rir,
                target_rir_max=deload_policy.maximum_rir,
                reason_code="scheduled_deload",
                reason="Scheduled deload: retain the ordinary repetitions, reduce each load by 30–40% in equipment steps and aim for RIR 3–4. Actual reserve is logged, not predicted.",
            )
        )
    return WorkoutRecommendation(phase, tuple(output))
