"""Block configuration persists independently of plan-version effective dates."""

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import db.migrate as migration_runner
from db.training_plans import (
    days,
    exercises,
    load_training_plan_version,
    load_training_plan_versions,
    load_training_plans,
    plans,
    progression_settings,
    save_training_plan,
    versions,
)
from models.training_plan import (
    PlannedExercise,
    ProgressionSettings,
    TrainingDay,
    TrainingPlanDraft,
)
from test_training_plan_view import create_plan, start_app
from test_training_plan_view import plan_engine as plan_engine


def draft(settings=None):
    return TrainingPlanDraft(
        "Upper",
        date.today() - timedelta(days=28),
        (
            TrainingDay(
                "Upper A", 0, (PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5),)
            ),
        ),
        settings,
    )


@pytest.mark.parametrize("weeks", [6, 7, 8])
def test_settings_roundtrip_and_revision_omission_preserves_block(plan_engine, weeks):
    migration_runner.migrate(plan_engine, apply=True)
    settings = ProgressionSettings(date.today() - timedelta(days=21), weeks)
    first = save_training_plan(plan_engine, draft(settings))
    assert first.draft.progression == settings
    assert load_training_plan_version(plan_engine, first.version_id) == first
    # Old clients may omit the new field when revising: do not reset the block.
    second = save_training_plan(
        plan_engine,
        replace(first.draft, effective_from=date.today(), progression=None),
        plan_id=first.plan_id,
    )
    assert second.draft.progression == settings
    assert second.draft.effective_from != settings.block_start
    assert load_training_plan_version(plan_engine, first.version_id) == first


def test_explicit_block_change_creates_new_snapshot(plan_engine):
    migration_runner.migrate(plan_engine, apply=True)
    first = save_training_plan(
        plan_engine, draft(ProgressionSettings(date.today() - timedelta(days=21), 6))
    )
    changed = ProgressionSettings(date.today(), 8)
    second = save_training_plan(
        plan_engine,
        replace(first.draft, effective_from=date.today(), progression=changed),
        plan_id=first.plan_id,
    )
    assert second.draft.progression == changed
    assert (
        load_training_plan_version(plan_engine, first.version_id).draft.progression.block_weeks == 6
    )


@pytest.mark.parametrize("weeks", [0, 5, 9, True, 6.5, None])
def test_invalid_block_lengths_are_rejected(weeks):
    with pytest.raises(ValueError, match="6, 7 or 8"):
        ProgressionSettings(date.today(), weeks)


def test_invalid_block_date_or_settings_type_are_rejected():
    with pytest.raises(ValueError, match="must be a date"):
        ProgressionSettings(datetime.now(), 7)
    with pytest.raises(ValueError, match="Invalid progression"):
        replace(draft(), progression={"block_weeks": 7})


def test_database_rejects_invalid_block_length(plan_engine):
    migration_runner.migrate(plan_engine, apply=True)
    saved = save_training_plan(plan_engine, draft())
    with pytest.raises(IntegrityError), plan_engine.begin() as connection:
        connection.execute(
            progression_settings.insert().values(
                version_id=saved.version_id, block_start=date.today(), block_weeks=5
            )
        )
    assert load_training_plan_version(plan_engine, saved.version_id).draft.progression is None


def test_upgrade_preserves_legacy_plan_without_assuming_a_block(plan_engine, monkeypatch):
    with monkeypatch.context() as temporary:
        temporary.setattr(migration_runner, "MIGRATIONS", migration_runner.MIGRATIONS[:4])
        migration_runner.migrate(plan_engine, apply=True)
    with plan_engine.begin() as connection:
        plan_id = connection.execute(plans.insert().values()).inserted_primary_key[0]
        version_id = connection.execute(
            versions.insert().values(
                plan_id=plan_id,
                version_number=1,
                name="Legacy",
                effective_from=date.today(),
            )
        ).inserted_primary_key[0]
        day_id = connection.execute(
            days.insert().values(version_id=version_id, name="Upper", weekday=0, position=1)
        ).inserted_primary_key[0]
        connection.execute(
            exercises.insert().values(
                day_id=day_id,
                exercise_id=1,
                position=1,
                set_count=3,
                target_min=6,
                target_max=10,
                target_unit="reps",
                target_rir=2,
                weight_increment=1.25,
            )
        )
    assert migration_runner.migrate(plan_engine, apply=True) == [
        "005_progression_settings",
        "006_set_loads",
        "007_recommendation_lineage",
        "008_starting_loads",
        "009_exercise_history_load_settings",
    ]
    assert migration_runner.migrate(plan_engine, apply=True) == []
    saved = load_training_plan_version(plan_engine, version_id)
    assert saved.draft.progression is None
    assert saved.draft.days[0].exercises[0].weight_increment == 1.25
    with plan_engine.connect() as connection:
        assert connection.execute(select(progression_settings)).all() == []


def test_form_saves_rir_weight_step_and_preserves_block_on_revision(plan_engine):
    app = start_app(plan_engine)
    origin = date.today() - timedelta(days=14)
    app.date_input(key="plan_editor_new_block_start").set_value(origin)
    app.selectbox(key="plan_editor_new_block_weeks").select(8)
    app.number_input(key="plan_editor_new_day_0_ex_0_increment").set_value(2.5)
    app.number_input(key="plan_editor_new_day_0_ex_0_rir").set_value(1)
    create_plan(app)
    first = load_training_plans(plan_engine)[0]
    assert first.draft.progression == ProgressionSettings(origin, 8)
    assert first.draft.days[0].exercises[0].weight_increment == 2.5
    assert first.draft.days[0].exercises[0].target_rir == 1
    app.toggle(key=f"plan_edit_{first.version_id}").set_value(True).run()
    scope = f"plan_editor_{first.version_id}"
    assert app.date_input(key=f"{scope}_block_start").value == origin
    assert app.selectbox(key=f"{scope}_block_weeks").value == 8
    app.number_input(key=f"{scope}_day_0_ex_0_minimum").set_value(8)
    app.button(key=f"{scope}_save").click().run()
    assert not app.exception
    assert not app.error
    history = load_training_plan_versions(plan_engine, first.plan_id)
    assert len(history) == 2
    assert history[0] == first
    assert history[1].draft.progression == first.draft.progression
    assert history[1].draft.days[0].exercises[0].weight_increment == 2.5


def test_legacy_form_does_not_silently_configure_block(plan_engine):
    migration_runner.migrate(plan_engine, apply=True)
    first = save_training_plan(plan_engine, draft())
    app = start_app(plan_engine)
    app.toggle(key=f"plan_edit_{first.version_id}").set_value(True).run()
    scope = f"plan_editor_{first.version_id}"
    assert not app.checkbox(key=f"{scope}_progression_enabled").value
    assert not any(item.key == f"{scope}_block_start" for item in app.date_input)
    app.button(key=f"{scope}_save").click().run()
    assert not app.exception
    assert load_training_plans(plan_engine)[0].draft.progression is None
