from statistics import mean
from math import sqrt

from metrics.input import MetricsInput
from metrics.utils import estimate_1rm


def _pearson(x, y):
    if len(x) != len(y) or len(x) < 2:
        return None

    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den_x = sqrt(sum((a - mx) ** 2 for a in x))
    den_y = sqrt(sum((b - my) ** 2 for b in y))

    return round(num / (den_x * den_y), 3) if den_x and den_y else None


def compute_correlations(input: MetricsInput) -> dict:
    """
    Compute correlations between fatigue, volume and strength progression.
    """

    if not input.sets:
        return {}

    volumes = []
    intensities = []

    for s in input.sets:
        volumes.append(s.weight * s.repetitions)
        intensities.append(estimate_1rm(s.weight, s.repetitions))

    correlations = {"volume_vs_strength": _pearson(volumes, intensities),}

    return correlations
