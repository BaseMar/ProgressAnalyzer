"""
Exercise-level training metrics.

This module computes metrics describing performance, volume,
intensity, and progress for each exercise across all sessions.
"""

from collections import defaultdict
from statistics import mean
from typing import Dict, Any, List

from metrics.input import MetricsInput
from metrics.utils import estimate_1rm


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

    # workout_exercise_id -> exercise_id
    workout_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}

    # workout_exercise_id -> session_date
    workout_to_date = {we.workout_exercise_id: we.session_date for we in input.workout_exercises}

    sets_by_exercise: Dict[int, List] = defaultdict(list)

    for workout_set in input.sets:
        exercise_id = workout_to_exercise.get(workout_set.workout_exercise_id)
        if exercise_id is None:
            continue

        sets_by_exercise[exercise_id].append(workout_set)

    per_exercise: Dict[int, Dict[str, Any]] = {}

    for exercise_id, sets in sets_by_exercise.items():
        total_sets = len(sets)
        total_reps = sum(s.repetitions for s in sets)
        total_volume = sum(s.repetitions * s.weight for s in sets)

        weights = [s.weight for s in sets]
        avg_weight = mean(weights)
        max_weight = max(weights)

        rirs = [s.rir for s in sets if s.rir is not None]
        avg_rir = mean(rirs) if rirs else None
        sets_to_failure = sum(1 for s in sets if s.rir == 0)

        # --- 1RM estimates ---
        one_rms = [estimate_1rm(s.weight, s.repetitions) for s in sets]

        estimated_1rm_max = max(one_rms)
        estimated_1rm_avg = mean(one_rms)

        # --- Progression (ordered by session date) ---
        sets_sorted = sorted(sets, key=lambda s: workout_to_date[s.workout_exercise_id])

        first_volume = (sets_sorted[0].repetitions * sets_sorted[0].weight)
        last_volume = (sets_sorted[-1].repetitions * sets_sorted[-1].weight)
        volume_trend = last_volume - first_volume

        first_1rm = estimate_1rm(sets_sorted[0].weight, sets_sorted[0].repetitions,)
        last_1rm = estimate_1rm(sets_sorted[-1].weight, sets_sorted[-1].repetitions,)
        strength_trend_1rm = last_1rm - first_1rm

        # --- Consistency ---
        sessions_count = len({workout_to_date[s.workout_exercise_id] for s in sets})
        avg_sets_per_session = total_sets / sessions_count

        per_exercise[exercise_id] = {
            "total_sets": total_sets,
            "total_reps": total_reps,
            "total_volume": total_volume,
            "avg_weight": avg_weight,
            "max_weight": max_weight,
            "estimated_1rm_max": estimated_1rm_max,
            "estimated_1rm_avg": estimated_1rm_avg,
            "avg_rir": avg_rir,
            "sets_to_failure": sets_to_failure,
            "volume_trend": volume_trend,
            "strength_trend_1rm": strength_trend_1rm,
            "sessions_count": sessions_count,
            "avg_sets_per_session": avg_sets_per_session,
        }

    # -------- Global aggregates --------

    global_metrics = {}

    if per_exercise:
        global_metrics = {
            "most_trained_exercise": max(per_exercise.items(),key=lambda x: x[1]["total_sets"],)[0],
            "highest_volume_exercise": max(per_exercise.items(),key=lambda x: x[1]["total_volume"],)[0],
            "strongest_exercise_1rm": max(per_exercise.items(),key=lambda x: x[1]["estimated_1rm_max"],)[0],
        }

    return {
        "per_exercise": per_exercise,
        "global": global_metrics,
    }
