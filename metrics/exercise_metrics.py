"""
Exercise-level training metrics.

This module computes metrics describing performance, volume,
intensity, and progress for each exercise across all sessions.
"""

from collections import defaultdict
from datetime import time
from statistics import mean
from typing import Any, Dict, List

from metrics.input import MetricsInput
from metrics.utils.set_values import analysis_sets, load_summary
from metrics.load_metrics import load_record, load_type, total_load_kg
from metrics.utils import (
    is_duration_set,
    set_duration_seconds,
    set_effective_sets,
    set_estimated_1rm,
    set_reps,
    set_volume,
    set_weight,
)


def compute_exercise_metrics(input: MetricsInput) -> Dict[str, Any]:
    """
    Compute exercise-level training metrics.

    Metrics are aggregated per exercise_id and include volume,
    intensity, estimated strength, progression, and consistency.

    Parameters
    ----------
    input : MetricsInput
        Normalized training data loaded from the database.

    Returns
    -------
    dict
        Dictionary with:
        - "per_exercise": dict[int, dict[str, Any]]
        - "global": dict[str, Any]
    """

    workout_to_exercise = {
        we.workout_exercise_id: we.exercise_id
        for we in input.workout_exercises
    }
    session_id_to_date = {s.session_id: s.session_date for s in input.sessions}
    sessions = {s.session_id: s for s in input.sessions}
    workout_to_session = {we.workout_exercise_id: we.session_id for we in input.workout_exercises}
    sets_by_exercise: Dict[int, List] = defaultdict(list)
    exercise_id_to_name = {e.exercise_id: e.name for e in input.exercises}
    exercise_id_to_bodypart = {e.exercise_id: e.body_part for e in input.exercises}
    targets_by_exercise: Dict[int, List[dict[str, Any]]] = defaultdict(list)
    progression_keys = {(item.workout_exercise_id, item.set_number)
                        for item in analysis_sets(input.sets, progression=True, deload_exercise_ids=input.deload_exercise_ids)}
    for target in input.exercise_muscle_targets:
        targets_by_exercise[target.exercise_id].append(
            {
                "muscle_group": target.muscle_group,
                "muscle_name": target.muscle_name,
                "role": target.role,
                "set_factor": target.set_factor,
            }
        )

    for workout_set in analysis_sets(input.sets, deload_exercise_ids=input.deload_exercise_ids):
        exercise_id = workout_to_exercise.get(workout_set.workout_exercise_id)
        if exercise_id is None:
            continue

        sets_by_exercise[exercise_id].append(workout_set)

    per_exercise: Dict[int, Dict[str, Any]] = {}

    for exercise_id, sets in sets_by_exercise.items():
        total_sets = len(sets)
        strength_sets = [s for s in sets if not is_duration_set(s)]
        duration_sets = [s for s in sets if is_duration_set(s)]
        total_reps = sum(set_reps(s) for s in strength_sets)
        total_volume = sum(set_volume(s) for s in sets)
        total_duration_seconds = sum(set_duration_seconds(s) for s in duration_sets)
        best_duration_seconds = (
            max(set_duration_seconds(s) for s in duration_sets)
            if duration_sets
            else None
        )
        effective_sets = sum(set_effective_sets(s) for s in sets)
        performance_points = []

        weights = [set_weight(s) for s in strength_sets]
        avg_weight = mean(weights) if weights else None
        max_weight = max(weights) if weights else None

        rirs = [s.rir for s in sets if s.rir is not None]
        avg_rir = mean(rirs) if rirs else None
        sets_to_failure = sum(1 for s in sets if s.rir == 0)

        one_rms = [
            estimated_1rm
            for s in strength_sets
            if (estimated_1rm := set_estimated_1rm(s)) is not None
        ]

        estimated_1rm_max = max(one_rms) if one_rms else None
        estimated_1rm_avg = mean(one_rms) if one_rms else None

        per_session_map = defaultdict(list)
        per_session_volume = defaultdict(int)
        per_session_duration = defaultdict(int)
        per_session_best_duration = defaultdict(int)
        unknown_volume_sessions = set()
        for s in sets:
            session_id = workout_to_session.get(s.workout_exercise_id)
            if session_id not in sessions:
                continue
            estimated_1rm = set_estimated_1rm(s)
            eligible = (s.workout_exercise_id, s.set_number) in progression_keys
            performance_points.append({"session_id": session_id, "date": session_id_to_date[session_id],
                "set_number": s.set_number, "workout_exercise_id": s.workout_exercise_id,
                "unit": "seconds" if is_duration_set(s) else "reps",
                "quantity": set_duration_seconds(s) if is_duration_set(s) else set_reps(s),
                "weight": set_weight(s), "eligible": eligible, "rir": s.rir, **load_record(s)})
            if not is_duration_set(s) and total_load_kg(s) is None:
                unknown_volume_sessions.add(session_id)
            if eligible and estimated_1rm is not None and estimated_1rm > 0:
                per_session_map[session_id].append(estimated_1rm)
            per_session_volume[session_id] += set_volume(s)
            per_session_duration[session_id] += set_duration_seconds(s)
            if eligible:
                per_session_best_duration[session_id] = max(
                    per_session_best_duration[session_id], set_duration_seconds(s),
                )

        session_order = sorted(per_session_volume, key=lambda sid: (
            sessions[sid].session_date, sessions[sid].start_time or time.min, sid,
        ))
        sessions_count = len(session_order)
        order_by_session = {sid: index for index, sid in enumerate(session_order)}
        for point in performance_points:
            point["session_order"] = order_by_session[point["session_id"]]
        avg_sets_per_session = total_sets / sessions_count if sessions_count else None

        per_session_1rm = [
            {"session_id": sid, "date": session_id_to_date[sid],
             "estimated_1rm": round(max(per_session_map[sid]), 2)}
            for sid in session_order if per_session_map[sid]
        ]

        per_session_volume_series = [
            {"session_id": sid, "date": session_id_to_date[sid], "volume": per_session_volume[sid]}
            for sid in session_order
        ]
        per_session_duration_series = [
            {"session_id": sid, "date": session_id_to_date[sid], "duration_seconds": per_session_duration[sid]}
            for sid in session_order if per_session_duration[sid]
        ]
        volume_trend = (
            per_session_volume[session_order[-1]] - per_session_volume[session_order[0]]
            if sessions_count >= 2 else None
        )
        strength_sessions = [sid for sid in session_order if per_session_map[sid]]
        strength_trend_1rm = (
            max(per_session_map[strength_sessions[-1]]) - max(per_session_map[strength_sessions[0]])
            if len(strength_sessions) >= 2 else None
        )
        duration_sessions = [sid for sid in session_order if per_session_best_duration[sid]]
        duration_trend_seconds = (
            per_session_best_duration[duration_sessions[-1]] - per_session_best_duration[duration_sessions[0]]
            if len(duration_sessions) >= 2 else None
        )
        # A single trend must not bridge a change in load convention or timed load.
        profiles = {(load_type(s), total_load_kg(s)) for s in duration_sets}
        if len(profiles) > 1 or any(load is None for _, load in profiles):
            duration_trend_seconds = None
        if len({load_type(s) for s in strength_sets}) > 1:
            strength_trend_1rm = None
            volume_trend = None
        if unknown_volume_sessions:
            volume_trend = None
        body_part = exercise_id_to_bodypart.get(exercise_id)
        muscle_targets = targets_by_exercise.get(exercise_id) or _fallback_muscle_targets(body_part)

        per_exercise[exercise_id] = {
            "exercise_name": exercise_id_to_name.get(exercise_id, f"Exercise {exercise_id}"),
            "body_part": body_part,
            "muscle_targets": muscle_targets,
            "muscle_target_summary": _muscle_target_summary(muscle_targets),
            "total_sets": total_sets,
            **load_summary(sets),
            "has_explicit_load": any(s.load is not None for s in sets),
            "per_set_performance": performance_points,
            "effective_sets": effective_sets,
            "total_reps": total_reps,
            "total_volume": total_volume,
            "total_duration_seconds": total_duration_seconds,
            "best_duration_seconds": best_duration_seconds,
            "avg_weight": avg_weight,
            "max_weight": max_weight,
            "estimated_1rm_max": estimated_1rm_max,
            "estimated_1rm_avg": estimated_1rm_avg,
            "avg_rir": avg_rir,
            "sets_to_failure": sets_to_failure,
            "volume_trend": volume_trend,
            "strength_trend_1rm": strength_trend_1rm,
            "duration_trend_seconds": duration_trend_seconds,
            "sessions_count": sessions_count,
            "avg_sets_per_session": avg_sets_per_session,
            "per_session_1rm": per_session_1rm,
            "per_session_volume": [dict(point, volume=None) if point["session_id"] in unknown_volume_sessions
                                   else point for point in per_session_volume_series],
            "per_session_duration": per_session_duration_series,
            "per_session_best_duration": [
                {"session_id": sid, "date": session_id_to_date[sid], "duration_seconds": per_session_best_duration[sid]}
                for sid in duration_sessions],
        }

    global_metrics = {}

    if per_exercise:
        global_metrics = {
            "most_trained_exercise": max(
                per_exercise.items(),
                key=lambda x: x[1]["total_sets"],
            )[0],
            "highest_volume_exercise": max(
                per_exercise.items(),
                key=lambda x: x[1]["total_volume"],
            )[0],
            "strongest_exercise_1rm": max(
                (
                    item
                    for item in per_exercise.items()
                    if item[1]["estimated_1rm_max"] is not None
                ),
                key=lambda x: x[1]["estimated_1rm_max"],
                default=(None, {}),
            )[0],
        }

    return {
        "per_exercise": per_exercise,
        "global": global_metrics,
    }


def _fallback_muscle_targets(body_part: str | None) -> list[dict[str, Any]]:
    if not body_part:
        return []

    return [
        {
            "muscle_group": body_part,
            "muscle_name": body_part,
            "role": "primary",
            "set_factor": 1.0,
        }
    ]


def _muscle_target_summary(muscle_targets: list[dict[str, Any]]) -> str:
    return "; ".join(
        f"{target['muscle_group']} ({target['role']}): {target['muscle_name']}"
        for target in muscle_targets
    )
