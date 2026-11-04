"""Regression cases for session comparisons and observed training frequency."""

from dataclasses import replace
from datetime import date, time

import pytest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.frequency_metrics import compute_frequency_metrics
from metrics.progress_metrics import compute_progress_metrics
from metrics.session_metrics import compute_session_metrics
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet


def training_input(sample_input, sessions, sets):
    return replace(
        sample_input, sessions=sessions, sets=sets,
        workout_exercises=[WorkoutExercise(s.session_id * 100, s.session_id, 1) for s in sessions],
    )


def test_one_session_with_many_sets_is_not_a_progress_comparison(sample_input):
    data = training_input(sample_input, [WorkoutSession(1, date(2026, 5, 1), None, None)], [
        WorkoutSet(100, 1, 10, 50., 2),
        WorkoutSet(100, 2, 8, 70., 1),
        WorkoutSet(100, 3, 6, 90., 0),
    ])
    assert compute_progress_metrics(data)["per_exercise"] == {}
    exercise = compute_exercise_metrics(data)["per_exercise"][1]
    assert exercise["strength_trend_1rm"] is None
    assert exercise["volume_trend"] is None


def test_best_session_result_is_independent_of_set_order_and_extra_warmup(sample_input):
    data = training_input(sample_input, [
        WorkoutSession(1, date(2026, 5, 1), None, None),
        WorkoutSession(2, date(2026, 5, 8), None, None),
    ], [
        WorkoutSet(100, 1, 10, 100., 1),
        WorkoutSet(100, 2, 10, 50., 3),
        WorkoutSet(200, 1, 10, 20., 4),
        WorkoutSet(200, 2, 10, 50., 3),
        WorkoutSet(200, 3, 10, 100., 1),
    ])
    progress = compute_progress_metrics(data)["per_exercise"][1]
    assert progress["exposure_count"] == 2
    assert progress["progress_pct"] == 0
    assert progress["start_1rm"] == progress["end_1rm"] == 133.33
    reversed_data = replace(data, sets=list(reversed(data.sets)))
    assert compute_progress_metrics(reversed_data) == compute_progress_metrics(data)
    exercise = compute_exercise_metrics(data)["per_exercise"][1]
    assert exercise["strength_trend_1rm"] == 0
    assert [point["estimated_1rm"] for point in exercise["per_session_1rm"]] == [133.33, 133.33]


def test_sessions_on_same_day_follow_start_time_and_count_separately(sample_input):
    data = training_input(sample_input, [
        WorkoutSession(1, date(2026, 5, 1), time(18), None),
        WorkoutSession(2, date(2026, 5, 1), time(8), None),
    ], [WorkoutSet(100, 1, 10, 110., 1), WorkoutSet(200, 1, 10, 100., 1)])

    progress = compute_progress_metrics(data)["per_exercise"][1]
    assert progress["exposure_count"] == 2
    assert progress["progress_pct"] == 10
    frequency = compute_frequency_metrics(data)
    assert frequency["global"]["sessions_per_week"] == 2
    assert frequency["global"]["avg_days_between_sessions"] == 0
    assert frequency["per_exercise"]["Bench Press"]["total_sessions"] == 2
    assert frequency["per_exercise"]["Bench Press"]["avg_days_between_sessions"] == 0
    assert frequency["per_muscle_group"]["Chest"]["total_sessions"] == 2
    exercise = compute_exercise_metrics(data)["per_exercise"][1]
    assert exercise["sessions_count"] == 2
    assert exercise["avg_sets_per_session"] == 1
    assert [point["session_id"] for point in exercise["per_session_1rm"]] == [2, 1]
    assert len(exercise["per_session_volume"]) == 2


def test_duration_progress_uses_longest_set_in_each_session(sample_input):
    data = training_input(sample_input, [
        WorkoutSession(1, date(2026, 5, 1), None, None),
        WorkoutSession(2, date(2026, 5, 8), None, None),
    ], [
        WorkoutSet(100, 1, 0, 0., None, duration_seconds=60),
        WorkoutSet(100, 2, 0, 0., None, duration_seconds=30),
        WorkoutSet(200, 1, 0, 0., None, duration_seconds=30),
        WorkoutSet(200, 2, 0, 0., None, duration_seconds=90),
    ])
    progress = compute_progress_metrics(data)["per_exercise"][1]
    assert progress["metric_type"] == "duration_seconds"
    assert progress["exposure_count"] == 2
    assert progress["progress_pct"] == 50
    assert compute_exercise_metrics(data)["per_exercise"][1]["duration_trend_seconds"] == 30


def test_empty_weeks_including_year_boundary_count_in_dashboard_and_frequency(sample_input):
    data = training_input(sample_input, [
        WorkoutSession(1, date(2025, 12, 22), None, None),
        WorkoutSession(2, date(2026, 1, 12), None, None),
    ], [WorkoutSet(100, 1, 10, 100., 1), WorkoutSet(200, 1, 10, 100., 1)])
    frequency = compute_frequency_metrics(data)
    assert frequency["global"]["sessions_per_week"] == 0.5
    assert frequency["per_exercise"]["Bench Press"]["sessions_per_week"] == 0.5
    assert frequency["per_muscle_group"]["Chest"]["sessions_per_week"] == 0.5
    assert compute_session_metrics(data)["global"]["avg_sessions_per_week"] == 0.5


def test_rare_exercise_uses_full_observation_period_and_repeated_entry_is_deduplicated(sample_input):
    frequency = compute_frequency_metrics(replace(
        sample_input,
        workout_exercises=sample_input.workout_exercises + [WorkoutExercise(104, 3, 2)],
    ))
    assert frequency["per_exercise"]["Row"]["total_sessions"] == 1
    assert frequency["per_exercise"]["Row"]["sessions_per_week"] == 0.33
    assert frequency["per_muscle_group"]["Back"]["sessions_per_week"] == 0.33


def test_progress_windows_weight_sessions_equally(sample_input):
    sessions = [WorkoutSession(i, date(2026, 5, i), None, None) for i in range(1, 9)]
    sets = [WorkoutSet(i * 100, 1, 1, float(i * 30), 1) for i in range(1, 9)]
    # Extra low-load sets in the final session must not dominate its window.
    sets.extend(WorkoutSet(800, i, 1, 10., 4) for i in range(2, 12))
    progress = compute_progress_metrics(training_input(sample_input, sessions, sets))["per_exercise"][1]
    assert progress["exposure_count"] == 8
    assert progress["start_1rm"] == pytest.approx(62.)
    assert progress["end_1rm"] == pytest.approx(217.)
    assert progress["progress_pct"] == 250


def test_empty_training_data_has_no_frequency_or_progress(sample_input):
    data = training_input(sample_input, [], [])
    assert compute_frequency_metrics(data) == {}
    assert compute_progress_metrics(data) == {}
    assert compute_session_metrics(data)["global"]["avg_sessions_per_week"] is None
