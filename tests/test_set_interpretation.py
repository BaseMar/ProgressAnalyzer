"""Automatic effort, audit provenance, immutable history and plan context."""
from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from test_plan_schedule import schedule_data
from test_plan_performance import data
from test_progression import PLAN, working, upcoming
from db.plan_adherence import actual_exercises, actual_sets, load_plan_adherence, load_plan_performance
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.training_context import load_deload_exercise_ids
from db.training_plans import save_training_plan
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.plan_adherence import compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.progression import recommend_normal_workout
from metrics.set_interpretation import interpret_sets
from metrics.training_block import deload_adjusted_input
from metrics.utils.set_values import analysis_sets
from models.training_plan import ProgressionSettings, TrainingDay
from models.workout_set import WorkoutSet
from ui.utils.data_filter import filter_data_by_month


def item(number=1, *, rir=2, weight=60., label=None, exercise=100, seconds=None):
    return WorkoutSet(exercise, number, 8 if not seconds else 0, weight, rir, seconds, label)


@pytest.mark.parametrize("rir, kind", [(0, "working"), (1, "working"), (3, "working"), (4, "light"), (5, "light"), (6, "low_effort"), (None, "unknown")])
def test_effort_boundaries_do_not_change_the_original_label(rir, kind):
    recorded = item(rir=rir)
    meaning = interpret_sets([recorded])[0]
    assert meaning.kind == kind
    assert meaning.progression_eligible == (kind == "working")
    assert recorded.is_warmup is None
    assert recorded.rir == rir


def test_warmup_requires_order_lower_load_and_a_later_working_set():
    warm, main = item(rir=5, weight=20.), item(2)
    meanings = interpret_sets([main, warm])
    assert [(value.kind, value.source) for value in meanings] == [("working", "rir"), ("warmup", "sequence")]
    assert interpret_sets([replace(warm, weight=60.), main])[0].kind == "light"
    assert interpret_sets([replace(warm, set_number=3), main])[0].kind == "light"
    assert interpret_sets([warm, replace(main, workout_exercise_id=200)])[0].kind == "light"
    assert interpret_sets([warm])[0].kind == "light"


def test_a_backoff_after_working_sets_is_not_inferred_as_warmup():
    sets = [item(), item(2, rir=4, weight=40.), item(3)]
    assert [meaning.kind for meaning in interpret_sets(sets)] == ["working", "light", "working"]


def test_explicit_corrections_win_without_turning_missing_rir_into_zero():
    sets = [item(label=True), item(2, rir=5, label=False), item(3, rir=None, label=False)]
    meanings = interpret_sets(sets)
    assert [meaning.kind for meaning in meanings] == ["warmup", "working", "working"]
    assert all(meaning.source == "explicit" for meaning in meanings)
    assert not meanings[-1].progression_eligible


@pytest.mark.parametrize("rir", [None, 4, 7])
def test_deload_context_preserves_light_work_but_never_confirms_normal_progress(rir):
    meaning = interpret_sets([item(rir=rir)], deload_exercise_ids={100})[0]
    assert (meaning.kind, meaning.source) == ("deload", "plan")
    assert meaning.counts_for_plan and meaning.descriptive
    assert not meaning.progression_eligible
    assert interpret_sets([item(rir=rir, label=True)], deload_exercise_ids={100})[0].kind == "warmup"


def test_timed_sets_are_not_discarded_for_missing_rir_or_inferred_as_warmups():
    sets = [item(rir=None, weight=0, seconds=30), item(2, rir=5, weight=0, seconds=60)]
    meanings = interpret_sets(sets)
    assert all(meaning.kind == "timed" and meaning.progression_eligible for meaning in meanings)
    assert analysis_sets(sets, progression=True) == sets


@pytest.mark.parametrize("rir", [-1, float("nan"), float("inf")])
def test_invalid_effort_does_not_support_comparisons(rir):
    assert interpret_sets([item(rir=rir)])[0].kind == "invalid"


def test_unknown_light_and_low_effort_stay_descriptive_without_becoming_primary_evidence():
    sets = [item(1, rir=None), item(2, rir=4), item(3, rir=7)]
    assert analysis_sets(sets) == sets
    assert analysis_sets(sets, progression=True) == []


def test_recorded_metrics_use_the_inferred_warmup_filter(sample_input):
    warmup = replace(sample_input.sets[0], set_number=0, weight=20., rir=5)
    with_warmup = replace(sample_input, sets=[warmup, *sample_input.sets])
    assert compute_exercise_metrics(with_warmup) == compute_exercise_metrics(sample_input)
    assert warmup.is_warmup is None


def test_recorded_performance_excludes_deload_without_removing_logged_volume(sample_input):
    deload_ids = frozenset({102})
    interpreted = replace(sample_input, deload_exercise_ids=deload_ids)
    metrics = compute_exercise_metrics(interpreted)
    assert sum(item["total_sets"] for item in metrics["per_exercise"].values()) == len(sample_input.sets)
    exercise = metrics["per_exercise"][1]
    assert exercise["strength_trend_1rm"] is None
    assert len(exercise["per_session_1rm"]) == 1
    assert len(exercise["per_session_volume"]) == 2


def test_unknown_effort_stays_in_muscle_workload_and_period_dates(sample_input):
    from ui.body_parts_view import BodyPartsView
    source = replace(sample_input, sets=[replace(value, rir=None) for value in sample_input.sets])
    metrics = compute_exercise_metrics(source)
    assert metrics["per_exercise"][1]["strength_trend_1rm"] is None
    view = BodyPartsView(metrics)
    assert len(view._metric_dates()) == 3
    frame = view._build_bodypart_df()
    assert frame.loc[frame["Body Part"] == "Chest", "Sessions"].item() == 2


def test_automatic_working_sets_support_confirmations_without_updating_raw_flags():
    entries = [working(sid, day, (10, 10, 10)) for sid, day in ((1, date(2026, 5, 11)), (2, date(2026, 5, 18)))]
    entries = [(workout, replace(actual, sets=tuple(replace(value, is_warmup=None) for value in actual.sets)), match)
               for workout, actual, match in entries]
    result = recommend_normal_workout(data(*entries), upcoming(), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert result.action == "increase_weight"
    assert result.goals[0].weight == 62.5
    assert all(value.is_warmup is None for entry in entries for value in entry[1].sets)


@pytest.mark.parametrize("rir, reason", [(4, "light_sets"), (6, "low_effort_sets")])
def test_light_work_is_not_recommended_as_an_ordinary_progression_baseline(rir, reason):
    entry = working(1, date(2026, 5, 18), rir=rir)
    entry = (entry[0], replace(entry[1], sets=tuple(replace(value, is_warmup=None) for value in entry[1].sets)), entry[2])
    result = recommend_normal_workout(data(entry), upcoming(), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert (result.action, result.reason_code, result.goals) == ("insufficient_data", reason, ())


def test_plan_counts_working_sets_after_warmup_without_crediting_light_backoffs():
    entry = working(1, date(2026, 5, 18))
    sets = [item(0, rir=5, weight=20.), *[replace(value, is_warmup=None) for value in entry[1].sets], item(4, rir=4, weight=40.)]
    entry = (entry[0], replace(entry[1], sets=tuple(sets)), entry[2])
    report = compute_plan_adherence(data(entry), as_of=date(2026, 5, 20))
    detail = report["workouts"][0]["details"][0]
    assert detail["covered_sets"] == 3
    assert all(meaning.kind == "working" for meaning in detail["set_interpretations"])
    assert detail["set_interpretations"][0].source == "rir"


def test_unknown_effort_counts_logged_work_but_not_a_progress_delta():
    first = working(1, date(2026, 5, 11))
    second = working(2, date(2026, 5, 18), rir=None)
    rows = compute_plan_performance(data(first, second), as_of=date(2026, 5, 20))
    assert rows[-1]["missing_sets"] == 0
    assert rows[-1]["reps_delta"] is None
    assert rows[-1]["sets"][0]["rir"] is None
    assert not rows[-1]["progression_eligible"]


def test_timed_recommendations_need_neither_explicit_labels_nor_target_rir():
    planned = replace(PLAN, target_unit="seconds", target_min=30, target_max=60, target_rir=None)
    entry = working(1, date(2026, 5, 18), (30, 40, 45), rir=None, planned=planned, weight=0.)
    entry = (entry[0], replace(entry[1], sets=tuple(replace(value, is_warmup=None) for value in entry[1].sets)), entry[2])
    result = recommend_normal_workout(data(entry), upcoming(planned), as_of=date(2026, 5, 20), block_start=date(2026, 5, 1))[0]
    assert (result.action, result.reason_code, result.target_rir) == ("increase_time", "more_time", None)
    assert [g.minimum for g in result.goals] == [35,40,45]
    assert len(result.goals) == 3


def test_partial_unlabelled_deload_is_counted_without_regression():
    settings = ProgressionSettings(date(2026, 5, 4), 7)
    entry = working(1, date(2026, 6, 15), (6, 6), weight=52.5, rir=4)
    entry = (entry[0], replace(entry[1], sets=tuple(replace(value, is_warmup=None) for value in entry[1].sets)), entry[2])
    source = data(entry)
    adjusted = deload_adjusted_input(source, {1: settings})
    report = compute_plan_adherence(adjusted, as_of=date(2026, 6, 22), settings_by_version={1: settings})
    assert report["summary"]["covered_sets"] == 2
    assert report["summary"]["planned_sets"] == 3
    row = compute_plan_performance(source, as_of=date(2026, 6, 22), settings_by_version={1: settings})[0]
    assert row["missing_sets"] == 1
    assert row["sets"][0]["set_kind"] == "deload"
    assert row["reps_delta"] is None


def test_filtering_month_preserves_deload_context(sample_input, sets_dataframe):
    source = replace(sample_input, deload_exercise_ids=frozenset({101, 103}))
    filtered, _ = filter_data_by_month(source, sets_dataframe, "2026-05")
    assert filtered.deload_exercise_ids == frozenset({101})


def test_database_context_uses_saved_block_and_never_persists_inference(schedule_data):
    engine, _, source, sessions = schedule_data
    origin, performed = date(2024, 4, 1), date(2024, 5, 13)
    saved = save_training_plan(engine, replace(source.draft, effective_from=origin,
        days=(TrainingDay("Upper A", 0, (PLAN,)),), progression=ProgressionSettings(origin, 7)))
    slot = load_scheduled_workouts(engine, saved.plan_id, performed, performed)[0]
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=performed))
        connection.execute(actual_exercises.insert().values(workout_exercise_id=200, session_id=2, exercise_id=1))
        connection.execute(actual_sets.insert(), [{"set_id": index, "workout_exercise_id": 200,
            "set_number": index, "repetitions": 6, "weight": 52.5, "rir": 4} for index in (1, 2)])
    assign_scheduled_session(engine, slot.day_id, performed, 2)
    assert load_deload_exercise_ids(engine, as_of=performed - timedelta(days=1)) == frozenset()
    assert load_deload_exercise_ids(engine, as_of=performed) == frozenset({200})
    history = load_plan_performance(engine, saved.plan_id, performed, performed)
    assert all(value.is_warmup is None for actual in history.recorded for value in actual.sets)
    from db.set_classifications import classifications
    with engine.connect() as connection:
        assert connection.execute(select(classifications)).all() == []
