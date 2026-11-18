from datetime import date

import pytest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.input import MetricsInput
from metrics.utils import estimate_1rm
from models.exercise import Exercise
from models.exercise_muscle_target import ExerciseMuscleTarget
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet


def test_estimate_1rm_uses_epley_formula():
    assert estimate_1rm(100, 10) == pytest.approx(133.333333)


def test_compute_exercise_metrics_aggregates_targets_and_progress(sample_input):
    result = compute_exercise_metrics(sample_input)
    bench = result["per_exercise"][1]

    assert bench["exercise_name"] == "Bench Press"
    assert bench["total_sets"] == 4
    assert bench["dynamic_sets"] == 4
    assert [point["volume"] for point in bench["per_session_volume"]] == [1880, 1970]
    assert bench["muscle_targets"][0] == {
        "muscle_group": "Chest",
        "muscle_name": "Pectoralis",
        "role": "primary",
        "set_factor": 1.0,
    }
    assert [point["estimated_1rm"] for point in bench["per_session_1rm"]] == [139.33, 145.67]


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

    assert plank["total_volume"] == 0
    assert plank["total_sets"] == plank["timed_sets"] == 2
    assert plank["dynamic_sets"] == 0
    assert [point["duration_seconds"] for point in plank["per_session_best_duration"]] == [45, 75]
    assert plank["duration_trend_seconds"] == 30
    assert plank["per_session_1rm"] == []


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

    assert bench["dynamic_sets"] == 1
    assert bench["timed_sets"] == 0
    assert bench["total_volume"] == 1000
    assert bench["per_set_performance"][0]["quantity"] == 10
    assert bench["per_session_duration"] == []
    assert bench["per_session_1rm"][0]["estimated_1rm"] == 133.33
