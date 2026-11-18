"""
Exercise-level training metrics.

This module computes metrics describing performance, volume,
intensity, and progress for each exercise across all sessions.
"""

from collections import defaultdict
from datetime import time
from typing import Any, Dict, List

from metrics.input import MetricsInput
from metrics.load_metrics import load_record, load_type, total_load_kg
from metrics.utils import (
    is_duration_set,
    set_duration_seconds,
    set_estimated_1rm,
    set_reps,
    set_volume,
    set_weight,
)
from metrics.utils.set_values import analysis_sets


def compute_exercise_metrics(input: MetricsInput) -> Dict[str, Any]:
    """
    Compute exercise-level training metrics.

    Metrics are aggregated per exercise_id for recorded history,
    estimated-strength trends, and muscle allocation.

    Parameters
    ----------
    input : MetricsInput
        Normalized training data loaded from the database.

    Returns
    -------
    dict
        Dictionary with:
        - "per_exercise": dict[int, dict[str, Any]]
    """

    workout_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}
    session_id_to_date = {s.session_id: s.session_date for s in input.sessions}
    sessions = {s.session_id: s for s in input.sessions}
    workout_to_session = {we.workout_exercise_id: we.session_id for we in input.workout_exercises}
    sets_by_exercise: Dict[int, List] = defaultdict(list)
    exercise_id_to_name = {e.exercise_id: e.name for e in input.exercises}
    exercise_id_to_bodypart = {e.exercise_id: e.body_part for e in input.exercises}
    targets_by_exercise: Dict[int, List[dict[str, Any]]] = defaultdict(list)
    progression_keys = {
        (item.workout_exercise_id, item.set_number)
        for item in analysis_sets(
            input.sets, progression=True, deload_exercise_ids=input.deload_exercise_ids
        )
    }
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
        total_volume = sum(set_volume(s) for s in sets)
        performance_points = []

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
            performance_points.append(
                {
                    "session_id": session_id,
                    "date": session_id_to_date[session_id],
                    "set_number": s.set_number,
                    "workout_exercise_id": s.workout_exercise_id,
                    "unit": "seconds" if is_duration_set(s) else "reps",
                    "quantity": set_duration_seconds(s) if is_duration_set(s) else set_reps(s),
                    "weight": set_weight(s),
                    "eligible": eligible,
                    "rir": s.rir,
                    **load_record(s),
                }
            )
            if not is_duration_set(s) and total_load_kg(s) is None:
                unknown_volume_sessions.add(session_id)
            if eligible and estimated_1rm is not None and estimated_1rm > 0:
                per_session_map[session_id].append(estimated_1rm)
            per_session_volume[session_id] += set_volume(s)
            per_session_duration[session_id] += set_duration_seconds(s)
            if eligible:
                per_session_best_duration[session_id] = max(
                    per_session_best_duration[session_id],
                    set_duration_seconds(s),
                )

        session_order = sorted(
            per_session_volume,
            key=lambda sid: (
                sessions[sid].session_date,
                sessions[sid].start_time or time.min,
                sid,
            ),
        )
        order_by_session = {sid: index for index, sid in enumerate(session_order)}
        for point in performance_points:
            point["session_order"] = order_by_session[point["session_id"]]

        per_session_1rm = [
            {
                "session_id": sid,
                "date": session_id_to_date[sid],
                "estimated_1rm": round(max(per_session_map[sid]), 2),
            }
            for sid in session_order
            if per_session_map[sid]
        ]

        per_session_volume_series = [
            {"session_id": sid, "date": session_id_to_date[sid], "volume": per_session_volume[sid]}
            for sid in session_order
        ]
        per_session_duration_series = [
            {
                "session_id": sid,
                "date": session_id_to_date[sid],
                "duration_seconds": per_session_duration[sid],
            }
            for sid in session_order
            if per_session_duration[sid]
        ]
        strength_sessions = [sid for sid in session_order if per_session_map[sid]]
        strength_trend_1rm = (
            max(per_session_map[strength_sessions[-1]]) - max(per_session_map[strength_sessions[0]])
            if len(strength_sessions) >= 2
            else None
        )
        duration_sessions = [sid for sid in session_order if per_session_best_duration[sid]]
        duration_trend_seconds = (
            per_session_best_duration[duration_sessions[-1]]
            - per_session_best_duration[duration_sessions[0]]
            if len(duration_sessions) >= 2
            else None
        )
        # A single trend must not bridge a change in load convention or timed load.
        profiles = {(load_type(s), total_load_kg(s)) for s in duration_sets}
        if len(profiles) > 1 or any(load is None for _, load in profiles):
            duration_trend_seconds = None
        if len({load_type(s) for s in strength_sets}) > 1:
            strength_trend_1rm = None
        body_part = exercise_id_to_bodypart.get(exercise_id)
        muscle_targets = targets_by_exercise.get(exercise_id) or _fallback_muscle_targets(body_part)

        per_exercise[exercise_id] = {
            "exercise_name": exercise_id_to_name.get(exercise_id, f"Exercise {exercise_id}"),
            "body_part": body_part,
            "muscle_targets": muscle_targets,
            "total_sets": total_sets,
            "dynamic_sets": len(strength_sets),
            "timed_sets": len(duration_sets),
            "per_set_performance": performance_points,
            "total_volume": total_volume,
            "strength_trend_1rm": strength_trend_1rm,
            "duration_trend_seconds": duration_trend_seconds,
            "per_session_1rm": per_session_1rm,
            "per_session_volume": [
                dict(point, volume=None)
                if point["session_id"] in unknown_volume_sessions
                else point
                for point in per_session_volume_series
            ],
            "per_session_duration": per_session_duration_series,
            "per_session_best_duration": [
                {
                    "session_id": sid,
                    "date": session_id_to_date[sid],
                    "duration_seconds": per_session_best_duration[sid],
                }
                for sid in duration_sessions
            ],
        }

    return {"per_exercise": per_exercise}


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
