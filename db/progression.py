"""Compatibility exports for the recommendation application's public entry points."""

from services.recommendations import (
    load_normal_workout_recommendations,
    load_workout_recommendations,
)

__all__ = ["load_normal_workout_recommendations", "load_workout_recommendations"]
