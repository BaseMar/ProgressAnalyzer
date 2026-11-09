from datetime import date

import pytest

from metrics.input import MetricsInput
from models.exercise import Exercise
from models.exercise_muscle_target import ExerciseMuscleTarget
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.utils import estimate_1rm


def test_estimate_1rm_uses_epley_formula():
    assert estimate_1rm(100, 10) == pytest.approx(133.333333)


def test_compute_exercise_metrics_aggregates_targets_and_progress(sample_input):
    result = compute_exercise_metrics(sample_input)
    bench = result["per_exercise"][1]

    assert bench["exercise_name"] == "Bench Press"
    assert bench["total_sets"] == 4
    assert bench["sessions_count"] == 2
    assert bench["avg_sets_per_session"] == 2
    # Total session volumes: 1880 kg -> 1970 kg, rather than individual sets.
    assert bench["volume_trend"] == 90
    assert "Chest (primary): Pectoralis" in bench["muscle_target_summary"]
    assert result["global"]["most_trained_exercise"] == 1


def test_compute_exercise_metrics_handles_duration_exercises():
    sample_sessions = [
        WorkoutSession(1, date(2026, 5, 1), None, None),
        WorkoutSession(2, date(2026, 5, 8), None, None),
    ]
    input_data = MetricsInput(
        sessions=sample_sessions,
        workout_exercises=[
            WorkoutExercise(101, 1, 1),
            WorkoutExercise(102, 2, 1),
        ],
        sets=[
            WorkoutSet(101, 1, 45, 0.0, 2, duration_seconds=45),
            WorkoutSet(102, 1, 75, 0.0, 1, duration_seconds=75),
        ],
        exercises=[Exercise(1, "Plank", None, "Abs")],
        exercise_muscle_targets=[
            ExerciseMuscleTarget(1, "Abs", "Rectus abdominis", "primary", 1.0),
        ],
        muscle_groups=["Abs"],
        body_measurements=[],
        body_composition=[],
    )

    result = compute_exercise_metrics(input_data)
    plank = result["per_exercise"][1]

    assert plank["total_reps"] == 0
    assert plank["total_volume"] == 0
    assert plank["total_duration_seconds"] == 120
    assert plank["best_duration_seconds"] == 75
    assert plank["effective_sets"] == pytest.approx(2.0)
    assert plank["estimated_1rm_max"] is None


def test_compute_exercise_metrics_treats_nan_duration_as_strength_set():
    input_data = MetricsInput(
        sessions=[WorkoutSession(1, date(2026, 5, 1), None, None)],
        workout_exercises=[WorkoutExercise(101, 1, 1)],
        sets=[WorkoutSet(101, 1, 10, 100.0, 2, duration_seconds=float("nan"))],
        exercises=[Exercise(1, "Bench Press", None, "Chest")],
        exercise_muscle_targets=[],
        muscle_groups=["Chest"],
        body_measurements=[],
        body_composition=[],
    )

    result = compute_exercise_metrics(input_data)
    bench = result["per_exercise"][1]

    assert bench["total_reps"] == 10
    assert bench["total_volume"] == 1000
    assert bench["total_duration_seconds"] == 0
    assert bench["estimated_1rm_max"] == pytest.approx(133.333333)
