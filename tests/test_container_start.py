"""Container restarts must preserve records and apply only pending migrations."""

import pytest
from sqlalchemy import func, inspect, select, text

from db.container_start import ensure_database
from db.migrate import ledger
from db.migrations import v009_exercise_history_load_settings
from db.schema import define_base_tables
from test_bootstrap import fresh_engine as fresh_engine


def test_container_initializes_demo_once_and_preserves_modified_records(fresh_engine):
    first = ensure_database(fresh_engine)
    assert first["created"] and len(first["migrations"]) == 9
    with fresh_engine.begin() as connection:
        connection.execute(
            text("UPDATE workout_sessions SET notes=:note"), {"note": "Keep my edits after restart"}
        )
        before = {
            name: connection.execute(select(func.count()).select_from(table)).scalar_one()
            for name, table in define_base_tables().tables.items()
        }
    second = ensure_database(fresh_engine)
    assert second == {"created": False, "migrations": []}
    with fresh_engine.connect() as connection:
        after = {
            name: connection.execute(select(func.count()).select_from(table)).scalar_one()
            for name, table in define_base_tables().tables.items()
        }
        assert connection.execute(
            text("SELECT DISTINCT notes FROM workout_sessions")
        ).scalars().all() == ["Keep my edits after restart"]
    assert after == before


def test_container_applies_a_pending_migration_without_regenerating_demo(fresh_engine):
    ensure_database(fresh_engine)
    with fresh_engine.begin() as connection:
        v009_exercise_history_load_settings.define_table(define_base_tables()).drop(connection)
        connection.execute(
            ledger.delete().where(ledger.c.revision == v009_exercise_history_load_settings.REVISION)
        )
        connection.execute(
            text("UPDATE workout_sessions SET notes=:note"), {"note": "Existing history"}
        )
    result = ensure_database(fresh_engine)
    assert result == {
        "created": False,
        "migrations": [v009_exercise_history_load_settings.REVISION],
    }
    with fresh_engine.connect() as connection:
        assert connection.execute(
            text("SELECT DISTINCT notes FROM workout_sessions")
        ).scalars().all() == ["Existing history"]
    assert "exercise_history_load_settings" in inspect(fresh_engine).get_table_names()


def test_container_refuses_unrecognized_schema_without_touching_records(fresh_engine):
    with fresh_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE existing_records (note VARCHAR(50))")
        connection.execute(text("INSERT INTO existing_records VALUES (:note)"), {"note": "Keep me"})
    with pytest.raises(ValueError, match="unrecognized"):
        ensure_database(fresh_engine)
    assert inspect(fresh_engine).get_table_names() == ["existing_records"]
    with fresh_engine.connect() as connection:
        assert (
            connection.execute(text("SELECT note FROM existing_records")).scalar_one() == "Keep me"
        )


def test_unknown_migration_prevents_container_start_without_reseeding(fresh_engine):
    ensure_database(fresh_engine)
    with fresh_engine.begin() as connection:
        connection.execute(ledger.insert().values(revision="999_future_change"))
    with pytest.raises(RuntimeError, match="unknown"):
        ensure_database(fresh_engine)
    with fresh_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM training_plans")).scalar_one() == 1
        assert (
            connection.execute(
                select(ledger.c.revision).where(ledger.c.revision == "999_future_change")
            ).scalar_one()
            == "999_future_change"
        )
