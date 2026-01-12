"""
Set-level training metrics.

This module computes global metrics describing training quality,
intensity, effort, and load across all performed sets.

    set -> 1 record from workoutsets
    failure -> RIR == 0
    heavy set -> estimated_1rm >= 0.8 * max_estimated_1rm
    RIR 3+ -> all >= 3
"""

from statistics import mean
from typing import Dict, Any

from metrics.input import MetricsInput
from metrics.utils import estimate_1rm


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
    total_reps = sum(s.repetitions for s in sets)
    total_volume = sum(s.repetitions * s.weight for s in sets)

    weights = [s.weight for s in sets]
    avg_weight = mean(weights)
    max_weight = max(weights)

    rirs = [s.rir for s in sets if s.rir is not None]
    avg_rir = mean(rirs) if rirs else None

    # --- RIR distribution ---
    rir_distribution = {
        "rir_0": sum(1 for s in sets if s.rir == 0),
        "rir_1": sum(1 for s in sets if s.rir == 1),
        "rir_2": sum(1 for s in sets if s.rir == 2),
        "rir_3_plus": sum(1 for s in sets if s.rir is not None and s.rir >= 3),
    }

    sets_to_failure = rir_distribution["rir_0"]
    failure_ratio = sets_to_failure / total_sets

    # --- Strength estimation ---
    one_rms = [estimate_1rm(s.weight, s.repetitions)for s in sets]
    avg_estimated_1rm = mean(one_rms)
    max_estimated_1rm = max(one_rms)

    # --- Density & quality ---
    avg_reps_per_set = total_reps / total_sets
    heavy_threshold = 0.8 * max_estimated_1rm
    heavy_sets = sum(1 for orm in one_rms if orm >= heavy_threshold)
    heavy_set_ratio = heavy_sets / total_sets

    return {
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_volume": total_volume,
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
