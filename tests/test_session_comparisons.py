"""Recorded session ordering, independent sets and timed performance series."""

from dataclasses import replace
from datetime import date, time

from metrics.exercise_metrics import compute_exercise_metrics
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
    exercise = compute_exercise_metrics(data)["per_exercise"][1]
    assert exercise["strength_trend_1rm"] == 0
    assert [point["estimated_1rm"] for point in exercise["per_session_1rm"]] == [133.33, 133.33]
    reordered = compute_exercise_metrics(replace(data, sets=list(reversed(data.sets))))["per_exercise"][1]
    assert reordered["per_session_1rm"] == exercise["per_session_1rm"]
    assert reordered["strength_trend_1rm"] == exercise["strength_trend_1rm"]


def test_sessions_on_same_day_follow_start_time_and_count_separately(sample_input):
    data = training_input(sample_input, [
        WorkoutSession(1, date(2026, 5, 1), time(18), None),
        WorkoutSession(2, date(2026, 5, 1), time(8), None),
    ], [WorkoutSet(100, 1, 10, 110., 1), WorkoutSet(200, 1, 10, 100., 1)])

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
    assert compute_exercise_metrics(data)["per_exercise"][1]["duration_trend_seconds"] == 30


def test_empty_training_data_has_no_recorded_series(sample_input):
    data = training_input(sample_input, [], [])
    assert compute_exercise_metrics(data) == {"per_exercise": {}, "global": {}}
