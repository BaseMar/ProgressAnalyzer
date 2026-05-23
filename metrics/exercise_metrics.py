"""
Exercise-level training metrics.

This module computes metrics describing performance, volume,
intensity, and progress for each exercise across all sessions.
"""

from collections import defaultdict
from datetime import date
from statistics import mean
from typing import Any, Dict, List

from metrics.input import MetricsInput
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
    workout_to_date = {
        we.workout_exercise_id: session_id_to_date.get(we.session_id)
        for we in input.workout_exercises
    }
    sets_by_exercise: Dict[int, List] = defaultdict(list)
    exercise_id_to_name = {e.exercise_id: e.name for e in input.exercises}
    exercise_id_to_bodypart = {e.exercise_id: e.body_part for e in input.exercises}
    targets_by_exercise: Dict[int, List[dict[str, Any]]] = defaultdict(list)
    for target in input.exercise_muscle_targets:
        targets_by_exercise[target.exercise_id].append(
            {
                "muscle_group": target.muscle_group,
                "muscle_name": target.muscle_name,
                "role": target.role,
                "set_factor": target.set_factor,
            }
        )

    for workout_set in input.sets:
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

        sets_sorted = sorted(
            sets,
            key=lambda s: workout_to_date.get(s.workout_exercise_id) or date.max,
        )

        first_volume = set_volume(sets_sorted[0])
        last_volume = set_volume(sets_sorted[-1])
        volume_trend = last_volume - first_volume

        strength_sets_sorted = [s for s in sets_sorted if not is_duration_set(s)]
        if strength_sets_sorted:
            first_1rm = set_estimated_1rm(strength_sets_sorted[0])
            last_1rm = set_estimated_1rm(strength_sets_sorted[-1])
            strength_trend_1rm = (
                last_1rm - first_1rm
                if first_1rm is not None and last_1rm is not None
                else None
            )
        else:
            strength_trend_1rm = None

        duration_sets_sorted = [s for s in sets_sorted if is_duration_set(s)]
        if duration_sets_sorted:
            duration_trend_seconds = (
                set_duration_seconds(duration_sets_sorted[-1])
                - set_duration_seconds(duration_sets_sorted[0])
            )
        else:
            duration_trend_seconds = None

        sessions_count = len(
            {
                workout_to_date.get(s.workout_exercise_id)
                for s in sets
                if workout_to_date.get(s.workout_exercise_id) is not None
            }
        )
        avg_sets_per_session = total_sets / sessions_count if sessions_count else None

        per_session_map = defaultdict(list)
        per_session_volume = defaultdict(int)
        per_session_duration = defaultdict(int)
        for s in sets:
            date = workout_to_date.get(s.workout_exercise_id)
            if date is None:
                continue
            estimated_1rm = set_estimated_1rm(s)
            if estimated_1rm is not None:
                per_session_map[date].append(estimated_1rm)
            per_session_volume[date] += set_volume(s)
            per_session_duration[date] += set_duration_seconds(s)

        per_session_1rm = [
            {"date": d, "estimated_1rm": round(mean(vals), 2)}
            for d, vals in sorted(per_session_map.items())
        ]

        per_session_volume_series = [
            {"date": d, "volume": v} for d, v in sorted(per_session_volume.items())
        ]
        per_session_duration_series = [
            {"date": d, "duration_seconds": v}
            for d, v in sorted(per_session_duration.items())
            if v
        ]
        body_part = exercise_id_to_bodypart.get(exercise_id)
        muscle_targets = targets_by_exercise.get(exercise_id) or _fallback_muscle_targets(body_part)

        per_exercise[exercise_id] = {
            "exercise_name": exercise_id_to_name.get(exercise_id, f"Exercise {exercise_id}"),
            "body_part": body_part,
            "muscle_targets": muscle_targets,
            "muscle_target_summary": _muscle_target_summary(muscle_targets),
            "total_sets": total_sets,
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
            "per_session_volume": per_session_volume_series,
            "per_session_duration": per_session_duration_series,
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
