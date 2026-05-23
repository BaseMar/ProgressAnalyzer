"""
Set-level training metrics.

This module computes global metrics describing training quality,
intensity, effort, and load across all performed sets.
"""

from statistics import mean
from typing import Dict, Any

from metrics.input import MetricsInput
from metrics.utils import (
    is_duration_set,
    set_duration_seconds,
    set_estimated_1rm,
    set_reps,
    set_volume,
    set_weight,
)


def compute_set_metrics(input: MetricsInput) -> Dict[str, Any]:
    """Compute global set-level training metrics.

    Parameters
    ----------
    input : MetricsInput
        Normalized training data loaded from the database.

    Returns
    -------
    dict
        Dictionary with aggregated set-level metrics.
    """

    sets = input.sets
    if not sets:
        return {}

    total_sets = len(sets)
    strength_sets = [s for s in sets if not is_duration_set(s)]
    total_reps = sum(set_reps(s) for s in strength_sets)
    total_volume = sum(set_volume(s) for s in sets)
    total_duration_seconds = sum(set_duration_seconds(s) for s in sets)

    weights = [set_weight(s) for s in strength_sets]
    avg_weight = mean(weights) if weights else None
    max_weight = max(weights) if weights else None

    rirs = [s.rir for s in sets if s.rir is not None]
    avg_rir = mean(rirs) if rirs else None

    rir_distribution = {
        "rir_0": sum(1 for s in sets if s.rir == 0),
        "rir_1": sum(1 for s in sets if s.rir == 1),
        "rir_2": sum(1 for s in sets if s.rir == 2),
        "rir_3_plus": sum(1 for s in sets if s.rir is not None and s.rir >= 3),
    }

    sets_to_failure = rir_distribution["rir_0"]
    failure_ratio = sets_to_failure / total_sets

    one_rms = [
        estimated_1rm
        for s in strength_sets
        if (estimated_1rm := set_estimated_1rm(s)) is not None
    ]
    avg_estimated_1rm = mean(one_rms) if one_rms else None
    max_estimated_1rm = max(one_rms) if one_rms else None

    avg_reps_per_set = total_reps / len(strength_sets) if strength_sets else None
    if max_estimated_1rm is not None:
        heavy_threshold = 0.8 * max_estimated_1rm
        heavy_sets = sum(1 for orm in one_rms if orm >= heavy_threshold)
        heavy_set_ratio = heavy_sets / len(strength_sets) if strength_sets else None
    else:
        heavy_set_ratio = None

    return {
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_volume": total_volume,
        "total_duration_seconds": total_duration_seconds,
        "avg_weight": avg_weight,
        "max_weight": max_weight,
        "avg_rir": avg_rir,
        "rir_distribution": rir_distribution,
        "sets_to_failure": sets_to_failure,
        "failure_ratio": failure_ratio,
        "avg_estimated_1rm": avg_estimated_1rm,
        "max_estimated_1rm": max_estimated_1rm,
        "avg_reps_per_set": avg_reps_per_set,
        "heavy_set_ratio": heavy_set_ratio,
    }
