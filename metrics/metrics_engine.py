from typing import Dict, Callable, Any


class MetricsEngine:
    """Run registered metrics from registry.py"""

    def __init__(self, registry: Dict[str, Callable]):
        self.registry = registry

    def compute_all(self, data: Any) -> Dict[str, Any]:
        """Run all metrics from registry..
            :param data: MetricsInput
            :return: dict {metric_name: result}"""
        
        results = {}

        for name, compute_fn in self.registry.items():
            try:
                results[name] = compute_fn(data)
            except Exception as e:
                results[name] = {
                    "error": str(e),
                    "status": "failed"
                }

        return results

    def compute(self, metric_name: str, data: Any) -> Any:
        """Run single metric."""

        if metric_name not in self.registry:
            raise ValueError(f"Metric '{metric_name}' is not registered")

        return self.registry[metric_name](data)
