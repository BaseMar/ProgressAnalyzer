import pytest

from metrics.body_metrics import (
    _calculate_metric_deltas,
    _calculate_proportion_ratios,
    _calculate_recomposition_quality,
    compute_body_metrics,
)
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.fatigue_metrics import compute_fatigue_metrics
from metrics.frequency_metrics import compute_frequency_metrics
from metrics.metrics_engine import compute_all_metrics
from metrics.progress_metrics import compute_progress_metrics
from metrics.session_metrics import compute_session_metrics
from metrics.set_metrics import compute_set_metrics
from metrics.utils import estimate_1rm


def test_estimate_1rm_uses_epley_formula():
    assert estimate_1rm(100, 10) == pytest.approx(133.333333)


def test_compute_set_metrics_returns_global_set_summary(sample_input):
    result = compute_set_metrics(sample_input)

    assert result["total_sets"] == 5
    assert result["total_reps"] == 48
    assert result["sets_to_failure"] == 1
    assert result["rir_distribution"] == {
        "rir_0": 1,
        "rir_1": 2,
        "rir_2": 1,
        "rir_3_plus": 1,
    }
    assert result["failure_ratio"] == pytest.approx(0.2)


def test_compute_session_metrics_handles_regular_and_overnight_sessions(sample_input):
    result = compute_session_metrics(sample_input)

    assert result["per_session"][1]["duration_minutes"] == 60
    assert result["per_session"][2]["duration_minutes"] == 60
    assert result["per_session"][1]["total_volume"] == 1880
    assert result["global"]["avg_sessions_per_week"] == pytest.approx(1.0)


def test_compute_exercise_metrics_aggregates_targets_and_progress(sample_input):
    result = compute_exercise_metrics(sample_input)
    bench = result["per_exercise"][1]

    assert bench["exercise_name"] == "Bench Press"
    assert bench["total_sets"] == 4
    assert bench["sessions_count"] == 2
    assert bench["avg_sets_per_session"] == 2
    assert bench["volume_trend"] == -80
    assert "Chest (primary): Pectoralis" in bench["muscle_target_summary"]
    assert result["global"]["most_trained_exercise"] == 1


def test_compute_progress_metrics_classifies_strength_direction(sample_input):
    result = compute_progress_metrics(sample_input)

    assert result["per_exercise"][1]["progress_pct"] > 0
    assert result["global"]["improving_exercises"] == 1
    assert result["global"]["avg_strength_progress_pct"] is not None


def test_compute_fatigue_metrics_returns_session_and_global_scores(sample_input):
    result = compute_fatigue_metrics(sample_input)

    assert set(result["per_session"]) == {1, 2, 3}
    assert result["per_session"][2]["sets_to_failure_ratio"] == 0.5
    assert result["global"]["avg_fatigue_score"] is not None


def test_compute_frequency_metrics_returns_global_and_group_frequency(sample_input):
    result = compute_frequency_metrics(sample_input)

    assert result["global"]["sessions_per_week"] == 1.0
    assert result["per_exercise"]["Bench Press"]["total_sessions"] == 2
    assert result["per_muscle_group"]["Chest"]["total_sessions"] == 2


def test_body_metric_helpers_handle_ratios_deltas_and_recomposition():
    assert _calculate_proportion_ratios(
        {"chest": 104.0, "waist": 80.0, "thigh": 60.0}
    ) == {"chest_to_waist": 1.3, "thigh_to_waist": 0.75}
    assert _calculate_metric_deltas([{"x": 1.0}, {"x": 2.25}], "x") == 1.25
    assert _calculate_recomposition_quality(2.0, 1.6)["recomposition_type"] == "lean_bulk"


def test_compute_body_metrics_joins_flat_measurements_by_date(sample_input):
    result = compute_body_metrics(sample_input)

    assert result["global"]["total_weight_change"] == 2.0
    assert result["proportions"]["chest_to_waist"] == 1.3
    assert result["deltas"]["waist"] == -2.0
    assert result["timeline"][-1]["biceps"] == 38.0
    assert result["insights"]


def test_compute_all_metrics_runs_registered_metric_groups(sample_input):
    result = compute_all_metrics(sample_input)

    assert {"sessions", "exercises", "sets", "frequency", "fatigue", "progress", "body"} <= set(result)
    assert "error" not in result["sessions"]
