from metrics.registry import METRIC_REGISTRY


def compute_all_metrics(metrics_input) -> dict:
    results = {}

    for name, fn in METRIC_REGISTRY.items():
        results[name] = fn(metrics_input)

    return results
