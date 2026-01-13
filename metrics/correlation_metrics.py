from statistics import mean
from math import sqrt
from typing import List, Optional, Dict

from metrics.input import MetricsInput
from metrics.utils.strength import estimate_1rm


def _pearson_correlation(x: List[float], y: List[float]) -> Optional[float]:
    """
    Compute Pearson correlation coefficient for two equal-length numeric series.

    Returns None if the input is invalid or variance is zero.
    """
    if len(x) != len(y) or len(x) < 2:
        return None

    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den_x = sqrt(sum((a - mx) ** 2 for a in x))
    den_y = sqrt(sum((b - my) ** 2 for b in y))

    if den_x == 0 or den_y == 0:
        return None

    return round(num / (den_x * den_y), 3)


def compute_correlations(input: MetricsInput) -> Dict[str, Optional[float]]:
    """
    Compute correlations between training volume and estimated strength.

    Notes:
    - Correlations are computed at SET level.
    - Results should be interpreted as exploratory insights, not causation.
    """

    if not input.sets or len(input.sets) < 2:
        return {}

    volumes: List[float] = []
    strengths: List[float] = []

    for s in input.sets:
        if s.weight <= 0 or s.repetitions <= 0:
            continue

        volume = s.weight * s.repetitions
        strength = estimate_1rm(s.weight, s.repetitions)

        if strength is None:
            continue

        volumes.append(volume)
        strengths.append(strength)

    return {
        "volume_vs_strength": _pearson_correlation(volumes, strengths)
    }
