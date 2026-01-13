import logging
from typing import Dict

from metrics.input import MetricsInput
from metrics.registry import METRIC_REGISTRY

logger = logging.getLogger(__name__)


def compute_all_metrics(metrics_input: MetricsInput) -> Dict[str, dict]:
    """
    Compute all registered metrics using a shared MetricsInput.

    Each metric group is executed independently. Failure in one metric
    does not affect others.
    """

    results: Dict[str, dict] = {}

    for name, fn in METRIC_REGISTRY.items():
        try:
            results[name] = fn(metrics_input) or {}
        except Exception as exc:
            logger.exception("Metric '%s' failed: %s", name, exc)
            results[name] = {"error": str(exc),}

    return results
