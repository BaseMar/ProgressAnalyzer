from metrics.body_metrics import compute_body_metrics
from metrics.correlation_metrics import compute_correlations
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.fatigue_metrics import compute_fatigue_metrics
from metrics.frequency_metrics import compute_frequency_metrics
from metrics.progress_metrics import compute_progress_metrics
from metrics.session_metrics import compute_session_metrics
from metrics.set_metrics import compute_set_metrics

METRIC_REGISTRY = {
    "sessions": compute_session_metrics,
    "exercises": compute_exercise_metrics,
    "sets": compute_set_metrics,
    "frequency": compute_frequency_metrics,
    "fatigue": compute_fatigue_metrics,
    "progress": compute_progress_metrics,
    "body": compute_body_metrics,
    "correlations": compute_correlations,
}

__all__ = ["METRIC_REGISTRY"]
