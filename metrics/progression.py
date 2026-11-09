"""Public entry points for the shared versioned recommendation engine."""

from metrics.recommendations import recommend_normal_workout, recommend_workout

__all__ = ["recommend_normal_workout", "recommend_workout"]
