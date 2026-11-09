"""Shared preview inputs preserve dates, evidence and substitution decisions."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import pytest

from data_manager import DataManager
from db.progression import load_workout_recommendations
from scripts.baseline_fixture import AS_OF, create_fixture
from services.recommendations import prepare_plan_context, recommend_prepared_workout


@pytest.fixture(scope="module")
def preview_context():
    engine, plan = create_fixture(weeks=2)
    context = prepare_plan_context(
        engine, plan.plan_id, AS_OF - timedelta(days=27), AS_OF + timedelta(days=28), as_of=AS_OF
    )
    try:
        yield engine, plan, context
    finally:
        engine.dispose()


@pytest.mark.parametrize("offset", range(5))
def test_shared_month_context_matches_a_single_workout_read(preview_context, offset):
    engine, plan, context = preview_context
    day = AS_OF + timedelta(days=offset)
    workout = next(w for w in context.history.workouts if w.slot.scheduled_date == day)
    prepared = context.prepare_workout(workout.slot.day_id, day)
    expected = load_workout_recommendations(
        engine, plan.plan_id, workout.slot.day_id, day, as_of=AS_OF
    )
    assert recommend_prepared_workout(engine, prepared) == expected
    assert prepared.history is context.history
    assert prepared.versions is context.versions


def test_substitution_reuses_prepared_history_without_reloading_the_plan(preview_context):
    engine, plan, context = preview_context
    workout = next(w for w in context.history.workouts if w.slot.scheduled_date == AS_OF)
    prepared = context.prepare_workout(workout.slot.day_id, AS_OF)
    options = dict(
        substitutions={workout.targets[0].plan_exercise_id: 9}, replacement_weight_steps={9: 5.0}
    )
    expected = load_workout_recommendations(
        engine, plan.plan_id, workout.slot.day_id, AS_OF, as_of=AS_OF, **options
    )
    with patch(
        "services.recommendations.load_plan_performance",
        side_effect=AssertionError("History reloaded"),
    ):
        ordinary = recommend_prepared_workout(engine, prepared)
        replacement = recommend_prepared_workout(engine, prepared, **options)
        assert recommend_prepared_workout(engine, prepared) == ordinary
    assert replacement == expected
    assert ordinary.exercises[0].actual_exercise_id == 1
    assert replacement.exercises[0].actual_exercise_id == 9


def test_broad_preview_window_preserves_the_recorded_history_cutoff(preview_context):
    engine, _, context = preview_context
    workout = next(w for w in context.history.workouts if w.slot.scheduled_date == AS_OF)
    result = recommend_prepared_workout(engine, context.prepare_workout(workout.slot.day_id, AS_OF))
    bench, _, pullup, curl, *_ = result.exercises
    assert [goal.weight for goal in bench.goals] == [
        62.5
    ] * 3  # Future 200 kg is outside the evidence cutoff.
    assert bench.target_rir == 3
    assert all(goal.weight == 0 and goal.load_type == "bodyweight" for goal in pullup.goals)
    assert [goal.weight for goal in curl.goals] == [12.0, 10.0, 10.0]


def test_context_rejects_unrelated_versions_and_unavailable_workouts(preview_context):
    engine, plan, context = preview_context
    with pytest.raises(ValueError, match="belong to the selected plan"):
        prepare_plan_context(
            engine,
            plan.plan_id,
            AS_OF,
            AS_OF,
            as_of=AS_OF,
            versions=(replace(plan, plan_id=plan.plan_id + 1),),
        )
    with pytest.raises(ValueError, match="not scheduled"):
        context.prepare_workout(-1, AS_OF)


def test_facade_accepts_an_isolated_engine_without_loading_configuration(preview_context):
    engine, plan, _ = preview_context
    with patch(
        "data_manager.get_engine", side_effect=AssertionError("Configured database accessed")
    ):
        manager = DataManager(engine=engine)
        context = manager.prepare_plan_context(plan.plan_id, AS_OF, AS_OF, as_of=AS_OF)
        workout = next(w for w in context.history.workouts if w.slot.scheduled_date == AS_OF)
        result = manager.recommend_prepared_workout(
            context.prepare_workout(workout.slot.day_id, AS_OF)
        )
    assert result.exercises[0].goals[0].weight == 62.5
