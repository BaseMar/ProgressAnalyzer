"""Exercise migrations, constraints and snapshot transactions on an isolated DB."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, timedelta

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, event, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.schema import CreateTable

from db.migrate import migrate
from db.training_plans import (
    days, exercises, plans, versions, load_effective_training_plan, load_training_plan_version,
    load_training_plan_versions, load_training_plans, save_training_plan,
)
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", future=True)

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        # Make SQLite transactional DDL behave like PostgreSQL for these tests.
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "begin")
    def begin(connection):
        connection.exec_driver_sql("BEGIN")

    metadata = MetaData()
    catalog = Table("exercises", metadata,
        Column("exercise_id", Integer, primary_key=True), Column("exercise_name", String(120)),
    )
    history = Table("workout_sessions", metadata, Column("session_id", Integer, primary_key=True))
    Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True))
    Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True))
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(catalog.insert(), [
            {"exercise_id": 1, "exercise_name": "Bench Press"},
            {"exercise_id": 2, "exercise_name": "Plank"},
        ])
        connection.execute(history.insert().values(session_id=77))
    yield engine
    engine.dispose()


@pytest.fixture
def draft():
    return TrainingPlanDraft("Upper / Core", date.today() - timedelta(days=30), (
        TrainingDay("Upper A", 0, (
            PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5),
            PlannedExercise(2, 2, 30, 60, "seconds"),
        )),
        TrainingDay("Upper B", 4, (PlannedExercise(1, 3, 10, 12),)),
    ))


def test_migration_preview_is_read_only_and_apply_is_repeatable(engine):
    assert migrate(engine) == ["001_training_plans", "002_plan_session_links", "003_exercise_matches", "004_set_classifications", "005_progression_settings", "006_set_loads", "007_recommendation_lineage", "008_starting_loads", "009_exercise_history_load_settings"]
    assert "schema_migrations" not in inspect(engine).get_table_names()
    assert migrate(engine, apply=True) == ["001_training_plans", "002_plan_session_links", "003_exercise_matches", "004_set_classifications", "005_progression_settings", "006_set_loads", "007_recommendation_lineage", "008_starting_loads", "009_exercise_history_load_settings"]
    assert migrate(engine, apply=True) == []
    assert migrate(engine) == []
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT session_id FROM workout_sessions").scalar_one() == 77
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM exercises").scalar_one() == 2


def test_plan_roundtrip_preserves_order_ranges_units_and_optional_values(engine, draft):
    migrate(engine, apply=True)
    saved = save_training_plan(engine, draft)
    assert saved.version_number == 1
    assert saved.draft == draft
    assert load_training_plan_version(engine, saved.version_id) == saved
    assert load_training_plans(engine) == [saved]
    with pytest.raises(FrozenInstanceError):
        saved.draft.name = "Changed"


def test_revision_keeps_previous_snapshot_and_catalog_returns_latest(engine, draft):
    migrate(engine, apply=True)
    old = save_training_plan(engine, draft)
    updated = replace(draft, name="New block", effective_from=date.today(), days=(
        TrainingDay("Upper A", 1, (PlannedExercise(1, 4, 8, 12),)),
    ))
    new = save_training_plan(engine, updated, plan_id=old.plan_id)
    assert new.version_number == 2
    assert new.plan_id == old.plan_id
    assert new.version_id != old.version_id
    assert load_training_plan_version(engine, old.version_id) == old
    assert load_training_plan_versions(engine, old.plan_id) == [old, new]
    assert load_training_plans(engine) == [new]


def test_invalid_revision_does_not_modify_history(engine, draft):
    migrate(engine, apply=True)
    saved = save_training_plan(engine, draft)
    for start in (draft.effective_from, date.today() - timedelta(days=1)):
        with pytest.raises(ValueError, match="backdated"):
            save_training_plan(engine, replace(draft, effective_from=start), plan_id=saved.plan_id)
    assert load_training_plan_versions(engine, saved.plan_id) == [saved]
    with pytest.raises(ValueError, match="not found"):
        save_training_plan(engine, draft, plan_id=999)
    assert load_training_plan_version(engine, 999) is None


def test_effective_snapshot_changes_only_on_its_start_date(engine, draft):
    migrate(engine, apply=True)
    old = save_training_plan(engine, draft)
    future = date.today() + timedelta(days=7)
    new = save_training_plan(engine, replace(draft, name="Next block", effective_from=future), plan_id=old.plan_id)
    assert load_effective_training_plan(engine, old.plan_id, draft.effective_from - timedelta(days=1)) is None
    assert load_effective_training_plan(engine, old.plan_id, draft.effective_from) == old
    assert load_effective_training_plan(engine, old.plan_id, future - timedelta(days=1)) == old
    assert load_effective_training_plan(engine, old.plan_id, future) == new
    assert load_effective_training_plan(engine, old.plan_id, future + timedelta(days=60)) == new


def test_missing_catalog_exercise_rolls_back_entire_plan(engine, draft):
    migrate(engine, apply=True)
    bad = replace(draft, days=(TrainingDay("Bad", 0, (
        PlannedExercise(1, 3, 6, 10), PlannedExercise(999, 3, 6, 10),
    )),))
    with pytest.raises(IntegrityError):
        save_training_plan(engine, bad)
    assert load_training_plans(engine) == []
    with engine.connect() as connection:
        for table in (plans, versions, days, exercises):
            assert connection.execute(select(table)).all() == []


@pytest.mark.parametrize("changes", [
    {"set_count": 0}, {"target_min": 12, "target_max": 6},
    {"target_unit": "kg"}, {"target_rir": -1}, {"weight_increment": 0},
    {"weight_increment": float("nan")}, {"weight_increment": float("inf")},
])
def test_invalid_exercise_targets_are_rejected(changes):
    with pytest.raises(ValueError):
        replace(PlannedExercise(1, 3, 6, 10), **changes)


@pytest.mark.parametrize("weekday", [-1, 7, True])
def test_invalid_weekdays_are_rejected(weekday):
    with pytest.raises(ValueError):
        TrainingDay("Upper", weekday, (PlannedExercise(1, 3, 6, 10),))


@pytest.mark.parametrize("changes", [
    {"set_count": 0}, {"target_min": 12, "target_max": 6},
    {"target_unit": "kg"}, {"target_rir": -1},
])
def test_database_enforces_target_constraints_too(engine, draft, changes):
    migrate(engine, apply=True)
    saved = save_training_plan(engine, draft)
    with engine.connect() as connection:
        day_id = connection.execute(select(days.c.day_id).where(days.c.version_id == saved.version_id)).scalars().first()
    values = dict(day_id=day_id, exercise_id=1, position=99, set_count=3,
                  target_min=6, target_max=10, target_unit="reps")
    values.update(changes)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(exercises.insert().values(**values))


def test_postgres_schema_compiles_with_catalog_foreign_key():
    sql = str(CreateTable(exercises).compile(dialect=postgresql.dialect()))
    assert "REFERENCES exercises (exercise_id) ON DELETE RESTRICT" in sql
    assert "SERIAL" in sql


def test_conflicting_schema_does_not_mark_migration_applied(engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE training_plan_days (unexpected INTEGER)")
    with pytest.raises(OperationalError):
        migrate(engine, apply=True)
    assert migrate(engine) == ["001_training_plans", "002_plan_session_links", "003_exercise_matches", "004_set_classifications", "005_progression_settings", "006_set_loads", "007_recommendation_lineage", "008_starting_loads", "009_exercise_history_load_settings"]
    assert "training_plans" not in inspect(engine).get_table_names()
