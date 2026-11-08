"""Plan identities survive edits while repeated positions remain distinct."""
from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import select

from db.migrate import migrate
from db.training_plans import exercise_lineage, save_training_plan
from metrics.plan_performance import comparison_context
from models.scheduled_workout import ScheduledWorkout
from test_training_plans import engine, draft


def test_lineage_survives_workout_rename_weekday_and_exercise_reorder(engine, draft):
    migrate(engine, apply=True)
    first = save_training_plan(engine, draft)
    old = first.draft.days[0]
    changed = replace(first.draft, effective_from=date.today(), days=(
        replace(old, name="Renamed", weekday=2, exercises=tuple(reversed(old.exercises))),
        first.draft.days[1],
    ))
    second = save_training_plan(engine, changed, plan_id=first.plan_id)
    assert [x.history_key for x in second.draft.days[0].exercises] == [x.history_key for x in reversed(old.exercises)]
    assert second.draft.days[1].exercises[0].history_key != old.exercises[0].history_key


def test_context_ignores_cosmetic_schedule_edits_but_keeps_order_and_targets(engine, draft):
    migrate(engine, apply=True)
    item = save_training_plan(engine, draft).draft.days[0].exercises[0]
    slot = ScheduledWorkout(1, 1, date(2026, 11, 2), "Upper A")
    renamed = replace(slot, day_id=2, version_id=2, scheduled_date=date(2026, 11, 5), name="Renamed")
    context = comparison_context(slot, 1, item, item.exercise_id)
    assert comparison_context(renamed, 1, item, item.exercise_id) == context
    assert comparison_context(renamed, 2, item, item.exercise_id) != context
    assert comparison_context(renamed, 1, replace(item, target_rir=3), item.exercise_id) != context


def test_repeated_exercise_positions_have_distinct_lineage(engine, draft):
    migrate(engine, apply=True)
    item = draft.days[0].exercises[0]
    changed = replace(draft, days=(replace(draft.days[0], exercises=(item, item)),))
    saved = save_training_plan(engine, changed)
    keys = [x.history_key for x in saved.draft.days[0].exercises]
    assert len(set(keys)) == 2
    invalid = replace(saved.draft, effective_from=date.today(), days=(
        replace(saved.draft.days[0], exercises=(saved.draft.days[0].exercises[0],) * 2),))
    with pytest.raises(ValueError, match="history key"):
        save_training_plan(engine, invalid, plan_id=saved.plan_id)
    with engine.connect() as connection:
        assert len(connection.execute(select(exercise_lineage)).all()) == 2
