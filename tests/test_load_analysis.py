"""Load-aware progress: body mass, assistance, time, conventions and missing data."""
from dataclasses import replace
from datetime import date, timedelta

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.metrics_engine import compute_all_metrics
from metrics.load_metrics import recorded_load
from metrics.muscle_volume import weekly_plan_sets
from metrics.plan_performance import compute_plan_performance
from metrics.progress_metrics import compute_progress_metrics
from metrics.progression import recommend_normal_workout
from metrics.training_insights import compute_training_insights
from metrics.set_interpretation import interpret_sets
from metrics.utils.set_values import set_effective_sets, set_estimated_1rm, set_intensity, set_volume
from models.set_load import SetLoad
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet
from ui.body_parts_view import BodyPartsView
from ui.utils.load_charts import load_history_chart
from ui.utils.plan_charts import exercise_history_chart

from test_plan_performance import data, execution
from test_progression import upcoming
from test_deload import recommend as recommend_deload

AS_OF = date(2026, 6, 1)
DYNAMIC = PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5)
TIMED = PlannedExercise(1, 3, 30, 60, "seconds")


def source(sample_input, observations, *, timed=False):
    sessions, workouts, sets = [], [], []
    for sid, (load, quantity) in enumerate(observations, 1):
        sessions.append(WorkoutSession(sid, date(2026, 5, 1) + timedelta(days=7 * (sid - 1)), None, None))
        workouts.append(WorkoutExercise(sid * 100, sid, 1))
        weight = load.external_weight_kg if isinstance(load, SetLoad) else load
        sets.append(WorkoutSet(sid * 100, 1, 0 if timed else quantity, weight, None if timed else 2,
            quantity if timed else None, False, load if isinstance(load, SetLoad) else None))
    return replace(sample_input, sessions=sessions, workout_exercises=workouts, sets=sets)


def entry(sid, load, quantity=8, *, timed=False, day=None):
    weight = load.external_weight_kg if isinstance(load, SetLoad) else load
    workout, recorded, match = execution(sid, day or date(2026, 5, 4) + timedelta(days=7 * (sid - 1)),
        (quantity,) * 3, weight=weight, planned=TIMED if timed else DYNAMIC)
    return workout, replace(recorded, sets=tuple(replace(item, is_warmup=False,
        load=load if isinstance(load, SetLoad) else None) for item in recorded.sets)), match


@pytest.mark.parametrize("load,total", [(SetLoad("bodyweight", 10, 80), 90), (SetLoad("assisted_bodyweight", 0, 80, 20), 60)])
def test_dynamic_volume_uses_total_supported_mass_without_bodyweight_e1rm(sample_input, load, total):
    inp = source(sample_input, [(load, 8)])
    item = inp.sets[0]
    assert set_volume(item) == total * 8
    assert set_estimated_1rm(item) is None
    assert set_intensity(item) is None
    all_metrics = compute_all_metrics(inp)
    assert all_metrics["sets"]["total_volume"] == total * 8
    assert all_metrics["sessions"]["per_session"][1]["total_volume"] == total * 8
    assert all_metrics["exercises"]["per_exercise"][1]["estimated_1rm_max"] is None


def test_unknown_mass_does_not_become_zero_load_or_complete_volume(sample_input):
    inp = source(sample_input, [(SetLoad("bodyweight", 5, None), 8)])
    all_metrics = compute_all_metrics(inp)
    exercise = all_metrics["exercises"]["per_exercise"][1]
    assert exercise["unknown_load_sets"] == 1
    assert not exercise["volume_complete"]
    assert exercise["per_session_volume"][0]["volume"] is None
    assert exercise["per_set_performance"][0]["total_load_kg"] is None
    assert all_metrics["sessions"]["per_session"][1]["unknown_total_load_sets"] == 1
    assert all_metrics["progress"]["per_exercise"] == {}


@pytest.mark.parametrize("kind", ["bodyweight", "assisted_bodyweight"])
def test_incomplete_bodyweight_record_never_treats_additional_kg_as_total(kind):
    assert recorded_load({"load_type": kind, "weight": 5}) is None


def test_heavy_set_ratio_uses_only_sets_with_supported_e1rm(sample_input):
    inp = source(sample_input, [(100., 8), (SetLoad("bodyweight", 5, 80), 8)])
    assert compute_all_metrics(inp)["sets"]["heavy_set_ratio"] == 1.0


def test_timed_work_has_no_tonnage_e1rm_or_duration_based_set_multiplier(sample_input):
    inp = source(sample_input, [(SetLoad("bodyweight", 5, 80), 90)], timed=True)
    assert set_volume(inp.sets[0]) == 0
    assert set_effective_sets(inp.sets[0]) == 1
    exercise = compute_exercise_metrics(inp)["per_exercise"][1]
    assert exercise["timed_sets"] == 1 and exercise["dynamic_sets"] == 0
    body = BodyPartsView({"per_exercise": {1: exercise}})._build_bodypart_df()
    assert body.loc[body["Body Part"] == "Chest", "Total_Sets"].item() == 0
    assert body.loc[body["Body Part"] == "Chest", "Timed_Sets"].item() == 1
    plan = TrainingPlanDraft("Mixed", date.today(), (TrainingDay("Day", 0, (TIMED, DYNAMIC)),))
    totals, missing = weekly_plan_sets(plan, inp)
    assert totals["Chest"] == 3
    assert not missing


def test_more_seconds_at_same_total_load_is_comparable(sample_input):
    load = SetLoad("bodyweight", 0, 80)
    inp = source(sample_input, [(load, 40), (load, 50)], timed=True)
    progress = compute_progress_metrics(inp)["per_exercise"][1]
    assert progress["metric_type"] == "duration_seconds"
    assert progress["comparison_load_kg"] == 80
    assert progress["progress_pct"] == 25
    row = compute_plan_performance(data(entry(1, load, 40, timed=True), entry(2, load, 50, timed=True)), as_of=AS_OF)[1]
    assert row["seconds_delta"] == 30
    assert row["sets"][0]["weight"] == 0
    assert row["sets"][0]["total_load_kg"] == 80


def test_body_mass_change_prevents_false_timed_improvement(sample_input):
    old, new = SetLoad("bodyweight", 0, 80), SetLoad("bodyweight", 0, 85)
    inp = source(sample_input, [(old, 40), (new, 50)], timed=True)
    assert compute_progress_metrics(inp)["per_exercise"] == {}
    assert compute_exercise_metrics(inp)["per_exercise"][1]["duration_trend_seconds"] is None
    rows = compute_plan_performance(data(entry(1, old, 40, timed=True), entry(2, new, 50, timed=True)), as_of=AS_OF)
    assert rows[1]["seconds_delta"] is None
    assert rows[1]["comparison"] == "Load changed: inspect individual sets"
    fig = exercise_history_chart(rows)
    assert list(fig.data[1].y) == [80, 85]
    assert fig.data[0].mode == "markers"


def test_assistance_reduction_increases_total_load_without_inventing_regression():
    old, new = SetLoad("assisted_bodyweight", 0, 80, 40), SetLoad("assisted_bodyweight", 0, 80, 20)
    observed = data(entry(1, old), entry(2, new))
    rows = compute_plan_performance(observed, as_of=AS_OF)
    assert [row["sets"][0]["total_load_kg"] for row in rows] == [40, 60]
    assert rows[1]["reps_delta"] is None
    insight = compute_training_insights(observed, as_of=AS_OF).annotations[0]
    assert insight.code == "load_changed"
    assert "60 kg total" in insight.evidence
    assert insight.sources[1].sets[0].assistance_kg == 20
    assert insight.sources[1].sets[0].total_load_kg == 60


def test_equal_total_with_different_body_and_external_mass_compares_reps(sample_input):
    old, new = SetLoad("bodyweight", 5, 80), SetLoad("bodyweight", 0, 85)
    inp = source(sample_input, [(old, 8), (new, 9)])
    progress = compute_progress_metrics(inp)
    assert progress["per_exercise"][1]["metric_type"] == "repetitions"
    assert progress["per_exercise"][1]["progress_pct"] == 12.5
    assert progress["global"]["avg_strength_progress_pct"] is None
    row = compute_plan_performance(data(entry(1, old), entry(2, new, 9)), as_of=AS_OF)[1]
    assert row["reps_delta"] == 3


@pytest.mark.parametrize("unknown", [SetLoad("bodyweight"), SetLoad("assisted_bodyweight", 0, 80, None)])
def test_unknown_load_blocks_comparisons_insights_and_recommendations(unknown):
    observed = data(entry(1, SetLoad("bodyweight", 0, 80)), entry(2, unknown, 10))
    rows = compute_plan_performance(observed, as_of=AS_OF)
    assert rows[1]["reps_delta"] is None
    assert "unknown" in rows[1]["comparison"]
    report = compute_training_insights(observed, as_of=AS_OF)
    assert report.assessed_contexts == 0
    result = recommend_normal_workout(observed, upcoming(), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert result.reason_code == "unknown_load" and not result.goals


def test_historical_convention_change_is_not_a_load_matched_comparison(sample_input):
    explicit = SetLoad("bodyweight", 0, 80)
    rows = compute_plan_performance(data(entry(1, 80.0, 40, timed=True), entry(2, explicit, 50, timed=True)), as_of=AS_OF)
    assert rows[1]["comparison"] == "Not comparable: load convention changed"
    assert rows[1]["seconds_delta"] is None
    inp = source(sample_input, [(80., 40), (explicit, 50)], timed=True)
    assert compute_progress_metrics(inp)["per_exercise"] == {}


def test_new_external_convention_needs_own_consecutive_confirmations():
    observed = data(entry(1, 60., 10), entry(2, SetLoad("external", 60), 10))
    result = recommend_normal_workout(observed, upcoming(), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert result.reason_code == "confirm_upper_range"


def test_return_to_old_convention_does_not_bridge_an_intervening_change(sample_input):
    inp = source(sample_input, [(60., 8), (SetLoad("external", 60), 9), (60., 10)])
    assert compute_progress_metrics(inp)["per_exercise"] == {}


@pytest.mark.parametrize("first_load,expected", [
    (SetLoad("assisted_bodyweight", 0, 80, 40), "warmup"),
    (SetLoad("assisted_bodyweight", 0, None, 40), "light"),
    (None, "light"),
])
def test_inferred_warmup_uses_total_load_and_same_convention(first_load, expected):
    first = WorkoutSet(100, 1, 8, 0, 4, load=first_load)
    second = WorkoutSet(100, 2, 8, 0, 2, load=SetLoad("assisted_bodyweight", 0, 80, 20))
    assert interpret_sets([first, second])[0].kind == expected


@pytest.mark.parametrize("load", [SetLoad("bodyweight", 10, 80), SetLoad("assisted_bodyweight", 0, 80, 20)])
def test_bodyweight_recommendations_do_not_guess_future_mass_or_reverse_assistance(load):
    observed = data(entry(1, load, 10), entry(2, load, 10))
    result = recommend_normal_workout(observed, upcoming(), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert result.reason_code == "bodyweight_load_manual" and not result.goals
    deload = recommend_deload(entry(1, load, day=date(2026, 6, 8))).exercises[0]
    assert deload.reason_code == "bodyweight_load_manual" and not deload.goals


def test_chart_separates_timed_load_profiles_and_unknown_load(sample_input):
    inp = source(sample_input, [(SetLoad("bodyweight", 0, 80), 40),
        (SetLoad("bodyweight", 5, 80), 30), (SetLoad("bodyweight", 0, None), 60)], timed=True)
    points = compute_exercise_metrics(inp)["per_exercise"][1]["per_set_performance"]
    fig = load_history_chart(points)
    assert list(fig.data[0].y) == [40, None, None]
    assert list(fig.data[1].y) == [None, 30, None]
    assert fig.data[2].mode == "markers"
    assert list(fig.data[-1].y) == [80, 85, None]


def test_recorded_exercise_ui_exposes_load_and_separates_workload(sample_input):
    inp = source(sample_input, [(SetLoad("bodyweight", 0, 80), 40), (SetLoad("bodyweight", 5, 80), 35)], timed=True)
    app = AppTest.from_string('''
import pandas as pd
import streamlit as st
from ui.exercise_view import ExerciseView
ExerciseView(st.session_state["metrics"], pd.DataFrame()).render(focused=True)
''', default_timeout=30)
    app.session_state["metrics"] = compute_exercise_metrics(inp)
    app.run()
    assert not app.exception and not app.error
    assert [item.value for item in app.metric] == ['85 kg total × 35 s', '2', '2']
    assert len(app.get("plotly_chart")) == 1
    assert not any("Body mass +" in item.value for item in app.caption)
    app.radio(key="recorded_exercise_series").set_value("Workload").run()
    assert not app.exception and len(app.get("plotly_chart")) == 1
