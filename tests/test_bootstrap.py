"""Fresh-install acceptance against real SQLite and isolated PostgreSQL schemas."""

import os
import subprocess
import sys
from datetime import date, time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateSchema, DropSchema
from streamlit.testing.v1 import AppTest

from data_loader import load_data
from data_manager import DataManager
from db.bootstrap import bootstrap_database
from db.connection import get_engine
from db.exercise_muscle_resolver import resolve_exercise
from db.migrate import MIGRATIONS, pending_migrations
from db.plan_adherence import load_plan_adherence
from db.queries import insert_exercise, upsert_exercise_muscle_targets
from db.schema import define_base_tables
from db.training_plans import load_training_plan_versions, load_training_plans
from metrics.plan_adherence import compute_plan_adherence

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 11, 10)


@pytest.fixture(params=["sqlite", "postgresql"])
def fresh_engine(request, tmp_path):
    if request.param == "sqlite":
        engine = create_engine(f"sqlite:///{tmp_path / 'fresh.sqlite3'}")
        try:
            yield engine
        finally:
            engine.dispose()
        return
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set TEST_POSTGRES_URL for fresh-schema PostgreSQL acceptance")
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    schema = "bootstrap_validation_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
            assert not connection.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name=:schema)"
                ),
                {"schema": schema},
            ).scalar_one()
        admin.dispose()


def test_fresh_schema_supports_real_catalog_and_workout_writes(fresh_engine):
    result = bootstrap_database(fresh_engine)
    assert result["migrations"] == [migration.REVISION for migration in MIGRATIONS]
    assert len(inspect(fresh_engine).get_table_names()) == 20
    assert not any(result["counts"].values())
    assert insert_exercise(fresh_engine, "Barbell Bench Press")
    with fresh_engine.begin() as connection:
        exercise_id = connection.execute(text("SELECT exercise_id FROM exercises")).scalar_one()
        upsert_exercise_muscle_targets(
            connection, exercise_id, resolve_exercise("Barbell Bench Press").targets
        )
    manager = DataManager(engine=fresh_engine)
    assert manager.add_workout_session(
        AS_OF,
        "Fresh install",
        [
            {
                "name": "Barbell Bench Press",
                "sets": [{"reps": 8, "weight": 60.0, "rir": 2}],
            }
        ],
        time(17),
        time(18),
    )
    frame = manager.load_sets_ui()
    assert len(frame) == 1 and frame.iloc[0].weight == 60.0
    assert manager.load_sessions().iloc[0].start_time is not None
    manager.add_body_measurements(
        dict(date=AS_OF, chest=100, waist=80, abdomen=85, hips=95, thigh=55, calf=35, biceps=32)
    )
    assert len(manager.load_body_data()["measurements"]) == 1
    with fresh_engine.connect() as connection:
        assert pending_migrations(connection) == []


def test_generated_demo_populates_every_route_and_preserves_load_meanings(fresh_engine):
    result = bootstrap_database(fresh_engine, demo=True, as_of=AS_OF)
    assert result["counts"]["exercises"] == 9
    assert result["counts"]["workout_sessions"] == 26
    assert result["counts"]["workout_sets"] == 370
    manager = DataManager(engine=fresh_engine)
    body = manager.load_body_data()
    assert len(body["composition"]) == len(body["measurements"]) == 9
    sets = manager.load_sets_ui()
    assert {"external", "bodyweight", "assisted_bodyweight"} <= set(sets.load_type)
    assert sets.duration_seconds.fillna(0).max() > 0
    assert sets.rir.isna().any()
    pullup = sets.loc[sets.exercise_name == "Pull-Up"]
    assert (pullup.weight == 0).all() and (pullup.body_mass_kg > 0).all()
    plan = load_training_plans(fresh_engine)[0]
    settings = {
        v.version_id: v.draft.progression
        for v in load_training_plan_versions(fresh_engine, plan.plan_id)
    }
    history = load_plan_adherence(fresh_engine, plan.plan_id, plan.draft.effective_from, AS_OF)
    coverage = compute_plan_adherence(history, as_of=AS_OF, settings_by_version=settings)
    linked = [row for row in coverage["workouts"] if row["linked"]]
    assert len(linked) == 25 and all(row["complete"] for row in linked)
    assert sum(row["performed_on"] != row["scheduled_date"] for row in linked) == 1
    assert len(history.matches) == 1


def test_bootstrap_refuses_existing_records_without_creating_tables(fresh_engine):
    with fresh_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE existing_notes (note VARCHAR(80))")
        connection.execute(
            text("INSERT INTO existing_notes VALUES (:note)"), {"note": "Keep this record"}
        )
    with pytest.raises(ValueError, match="not empty"):
        bootstrap_database(fresh_engine, demo=True)
    assert inspect(fresh_engine).get_table_names() == ["existing_notes"]
    with fresh_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT note FROM existing_notes")).scalar_one()
            == "Keep this record"
        )


def test_repeated_initialization_does_not_duplicate_demo_records(fresh_engine):
    bootstrap_database(fresh_engine, demo=True, as_of=AS_OF)
    tables = define_base_tables().tables

    def counts():
        with fresh_engine.connect() as connection:
            return {
                name: connection.execute(select(func.count()).select_from(table)).scalar_one()
                for name, table in tables.items()
            }

    before = counts()
    with pytest.raises(ValueError, match="not empty"):
        bootstrap_database(fresh_engine, demo=True, as_of=AS_OF)
    assert counts() == before


def test_failed_seed_rolls_back_base_schema_and_migrations(fresh_engine, monkeypatch):
    def fail(scope, tables, *, as_of):
        scope.connection.execute(
            tables["exercises"].insert().values(exercise_name="Temporary record")
        )
        raise RuntimeError("Interrupted demo seed")

    monkeypatch.setattr("db.demo_data.seed_demo", fail)
    with pytest.raises(RuntimeError, match="Interrupted"):
        bootstrap_database(fresh_engine, demo=True, as_of=AS_OF)
    assert inspect(fresh_engine).get_table_names() == []


def test_cli_uses_only_the_explicit_target(tmp_path):
    target = tmp_path / "demo.sqlite3"
    untouched = tmp_path / "configured.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "db.bootstrap",
            "--url",
            f"sqlite:///{target}",
            "--demo",
            "--as-of",
            AS_OF.isoformat(),
        ],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{untouched}"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Exercises: 9; sessions: 26; sets: 370" in result.stdout
    assert target.exists() and not untouched.exists()


def test_sqlite_app_connections_enforce_foreign_keys_and_cascade_session_deletion(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'connections.sqlite3'}")
    get_engine.clear()
    engine = get_engine()
    try:
        bootstrap_database(engine, demo=True, as_of=AS_OF)
        with engine.connect() as first, engine.connect() as second:
            assert first.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert second.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO workout_exercises (session_id,exercise_id) VALUES (9999,1)"
            )
        manager = DataManager(engine=engine)
        with engine.connect() as connection:
            session_id = connection.execute(
                text("SELECT session_id FROM training_plan_exercise_matches")
            ).scalar_one()
        assert manager.delete_session(session_id)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM training_plan_exercise_matches")
                ).scalar_one()
                == 0
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        get_engine.clear()
        engine.dispose()


@pytest.mark.parametrize("page", ["Overview", "Analysis", "Plan", "History"])
@pytest.mark.parametrize("demo", [False, True])
def test_fresh_database_renders_actual_entry_point_without_app_database(tmp_path, page, demo):
    engine = create_engine(f"sqlite:///{tmp_path / 'ui.sqlite3'}")
    bootstrap_database(engine, demo=demo)
    load_data.clear()
    try:
        with patch("data_manager.get_engine", return_value=engine):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
            app.session_state["nav_selected"] = page
            app.run()
            assert not app.exception and not app.error
            assert app.sidebar.button(key="nav_" + page)
    finally:
        load_data.clear()
        engine.dispose()
