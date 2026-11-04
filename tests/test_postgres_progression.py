"""Opt-in PostgreSQL verification in a fresh schema rolled back after each test.

TEST_POSTGRES_URL is explicit: the suite never falls back to DATABASE_URL.
The database role needs permission to create a schema. All legacy fixture tables,
migrations and synthetic logs live in that transaction's isolated search path.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, MetaData, String, Table, Time, create_engine, func, select, text
from sqlalchemy.schema import CreateSchema

from db.migrate import migrate
from db.plan_adherence import actual_exercises, actual_sets, load_plan_adherence, load_plan_performance, save_exercise_match
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.set_classifications import classifications
from db.training_plans import load_training_plan_version, save_training_plan
from metrics.plan_performance import compute_plan_performance
from models.training_plan import PlannedExercise, ProgressionSettings, TrainingDay, TrainingPlanDraft

pytestmark = pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Set TEST_POSTGRES_URL for isolated PostgreSQL integration tests")
ORIGIN = date(2024, 4, 1)
FIRST, SECOND, NEXT = date(2024, 4, 22), date(2024, 4, 29), date(2024, 5, 6)
DELOAD, RETURN = date(2024, 5, 13), date(2024, 5, 20)


class TransactionEngine:
    """Let repository services share one transaction without committing it."""
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


@pytest.fixture
def postgres():
    engine = create_engine(os.environ["TEST_POSTGRES_URL"])
    assert engine.dialect.name == "postgresql", "TEST_POSTGRES_URL must identify PostgreSQL"
    schema = "progress_validation_" + uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(CreateSchema(schema))
            quoted = connection.dialect.identifier_preparer.quote(schema)
            connection.execute(text(f"SET LOCAL search_path TO {quoted}"))
            metadata = MetaData()
            catalog = Table("exercises", metadata,
                Column("exercise_id", Integer, primary_key=True), Column("exercise_name", String))
            Table("workout_sessions", metadata, Column("session_id", Integer, primary_key=True),
                Column("session_date", Date), Column("start_time", Time), Column("end_time", Time), Column("notes", String))
            Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True),
                Column("session_id", ForeignKey("workout_sessions.session_id")), Column("exercise_id", ForeignKey("exercises.exercise_id")))
            Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True),
                Column("workout_exercise_id", ForeignKey("workout_exercises.workout_exercise_id")),
                Column("set_number", Integer), Column("repetitions", Integer), Column("weight", Float),
                Column("rir", Integer), Column("duration_seconds", Integer))
            metadata.create_all(connection)
            connection.execute(catalog.insert(), [
                {"exercise_id": 1, "exercise_name": "Barbell Bench Press"},
                {"exercise_id": 2, "exercise_name": "Machine Chest Press"},
            ])
            adapter = TransactionEngine(connection)
            assert len(migrate(adapter, apply=True)) == 5
            yield adapter
        finally:
            transaction.rollback()
            # Even a failing test must leave no schema, tables or fixture rows.
            remaining = connection.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=:schema)"), {"schema": schema}).scalar_one()
            assert not remaining, "Verification schema survived rollback"
    engine.dispose()


def plan(engine):
    return save_training_plan(engine, TrainingPlanDraft("PostgreSQL verification", ORIGIN, (
        TrainingDay("Upper A", 0, (PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5),)),
    ), ProgressionSettings(ORIGIN, 7)))


def log(engine, saved, sid, day, values=(10, 10, 10), *, actual_id=1, weight=60., rir=2):
    from db.plan_schedule import sessions
    slot = load_scheduled_workouts(engine, saved.plan_id, day, day)[0]
    with engine.begin() as connection:
        connection.execute(sessions.insert().values(session_id=sid, session_date=day))
        connection.execute(actual_exercises.insert().values(workout_exercise_id=sid * 100, session_id=sid, exercise_id=actual_id))
        items = [{"set_id": sid * 10, "workout_exercise_id": sid * 100, "set_number": 1,
                  "repetitions": 20, "weight": 20., "rir": 5}]
        items += [{"set_id": sid * 10 + number, "workout_exercise_id": sid * 100, "set_number": number + 1,
                   "repetitions": reps, "weight": weight, "rir": rir} for number, reps in enumerate(values, start=1)]
        connection.execute(actual_sets.insert(), items)
        connection.execute(classifications.insert(), [{"set_id": item["set_id"], "is_warmup": index == 0} for index, item in enumerate(items)])
    assign_scheduled_session(engine, slot.day_id, day, sid)
    if actual_id != 1:
        target = load_plan_adherence(engine, saved.plan_id, day, day).workouts[0].targets[0]
        save_exercise_match(engine, sid, target.plan_exercise_id, sid * 100)


def recommend(engine, saved, day, **options):
    slot = load_scheduled_workouts(engine, saved.plan_id, day, day)[0]
    return load_workout_recommendations(engine, saved.plan_id, slot.day_id, day, as_of=day, **options)


@pytest.mark.parametrize("values, action, expected_weight, expected_reps", [
    ((10, 10, 9), "increase_reps", 60., 10),
    ((10, 10, 10), "increase_weight", 62.5, 6),
])
def test_normal_goals_use_postgres_dates_labels_and_cross_month_history(postgres, values, action, expected_weight, expected_reps):
    saved = plan(postgres)
    log(postgres, saved, 1, FIRST, values)
    log(postgres, saved, 2, SECOND, values)
    with postgres.connect() as connection:
        connection.execute(classifications.delete())
        before = connection.execute(select(actual_sets).order_by(actual_sets.c.set_id)).mappings().all()
    item = recommend(postgres, saved, NEXT).exercises[0]
    assert item.action == action
    assert [(goal.weight, goal.minimum) for goal in item.goals] == [(expected_weight, expected_reps)] * 3
    assert item.evidence_dates[-1] == SECOND
    with postgres.connect() as connection:
        assert connection.execute(select(actual_sets).order_by(actual_sets.c.set_id)).mappings().all() == before
        assert connection.execute(select(classifications)).all() == []


def test_deload_return_and_analytical_coverage_on_postgres(postgres):
    saved = plan(postgres)
    for sid, day in enumerate((FIRST, SECOND, NEXT), start=1):
        log(postgres, saved, sid, day)
    lighter = recommend(postgres, saved, DELOAD).exercises[0]
    assert (lighter.action, lighter.target_rir) == ("deload", 4)
    assert [(goal.weight, goal.minimum) for goal in lighter.goals] == [(52.5, 6)] * 2
    log(postgres, saved, 4, DELOAD, (6, 6), weight=52.5, rir=4)
    with postgres.connect() as connection:
        connection.execute(classifications.delete())
    resumed = recommend(postgres, saved, RETURN)
    item = resumed.exercises[0]
    assert resumed.block.cycle == 2
    assert (item.action, item.reason_code, item.evidence_session_ids) == ("maintain", "resume_after_deload", (3,))
    assert [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals] == [(60., 6, 10)] * 3
    rows = compute_plan_performance(load_plan_performance(postgres, saved.plan_id, DELOAD, RETURN),
        as_of=RETURN, start=DELOAD, end=RETURN, settings_by_version={saved.version_id: saved.draft.progression})
    observed = next(row for row in rows if row["session_id"] == 4)
    assert (observed["training_phase"], observed["missing_sets"], observed["reps_delta"]) == ("deload", 0, None)
    from db.training_context import load_deload_exercise_ids
    assert load_deload_exercise_ids(postgres, as_of=RETURN) == frozenset({400})


def test_confirmed_substitute_keeps_own_load_step_and_never_edits_plan_on_postgres(postgres):
    saved = plan(postgres)
    log(postgres, saved, 1, FIRST, actual_id=2)
    log(postgres, saved, 2, SECOND, actual_id=2)
    target = load_plan_adherence(postgres, saved.plan_id, NEXT, NEXT).workouts[0].targets[0]
    original = recommend(postgres, saved, NEXT).exercises[0]
    assert original.reason_code == "no_normal_baseline"
    choices = {target.plan_exercise_id: 2}
    assert recommend(postgres, saved, NEXT, substitutions=choices).exercises[0].reason_code == "missing_weight_step"
    actual = recommend(postgres, saved, NEXT, substitutions=choices, replacement_weight_steps={2: 5.}).exercises[0]
    assert actual.action == "increase_weight"
    assert [goal.weight for goal in actual.goals] == [65.] * 3
    assert load_training_plan_version(postgres, saved.version_id) == saved
    with postgres.connect() as connection:
        assert connection.execute(select(func.count()).select_from(actual_sets)).scalar_one() == 8


def test_migrations_and_versioned_block_settings_roundtrip_on_postgres(postgres):
    saved = plan(postgres)
    revised = save_training_plan(postgres, replace(saved.draft, effective_from=date.today() + timedelta(days=1), progression=None), plan_id=saved.plan_id)
    assert revised.draft.progression == ProgressionSettings(ORIGIN, 7)
    assert load_training_plan_version(postgres, saved.version_id) == saved
    assert migrate(postgres) == []
    assert migrate(postgres, apply=True) == []
