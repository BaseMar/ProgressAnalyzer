"""Native snapshots must preserve all data and refuse occupied destinations."""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from data_manager import DataManager
from db.backup import BackupError, create_backup, restore_backup
from db.bootstrap import bootstrap_database

ROOT = Path(__file__).resolve().parents[1]


def snapshot(engine):
    with engine.connect() as connection:
        return {
            name: sorted(
                json.dumps(tuple(row), default=str)
                for row in connection.exec_driver_sql(
                    "SELECT * FROM " + connection.dialect.identifier_preparer.quote(name)
                )
            )
            for name in inspect(connection).get_table_names()
        }


def test_sqlite_backup_roundtrip_and_protected_targets(tmp_path):
    source = create_engine(f"sqlite:///{tmp_path / 'source.sqlite3'}")
    restored = create_engine(f"sqlite:///{tmp_path / 'restored.sqlite3'}")
    try:
        bootstrap_database(source, demo=True)
        before = snapshot(source)
        backup = create_backup(str(source.url), tmp_path / "snapshot.sqlite3")
        assert snapshot(source) == before
        with pytest.raises(BackupError, match="already exists"):
            create_backup(str(source.url), backup)
        with pytest.raises(BackupError, match="new SQLite filename"):
            restore_backup(str(source.url), backup)
        restore_backup(str(restored.url), backup)
        assert snapshot(restored) == before
        with restored.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert DataManager(engine=restored).add_exercise("Chest Dip")
        assert snapshot(source) == before
    finally:
        source.dispose()
        restored.dispose()


def test_failed_sqlite_backup_leaves_no_output_or_source_file(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        create_backup(f"sqlite:///{missing}", tmp_path / "backup.sqlite3")
    assert not list(tmp_path.iterdir())


def test_corrupt_sqlite_restore_keeps_target_absent(tmp_path):
    backup = tmp_path / "corrupt.sqlite3"
    backup.write_bytes(b"invalid database")
    target = tmp_path / "target.sqlite3"
    with pytest.raises(sqlite3.DatabaseError):
        restore_backup(f"sqlite:///{target}", backup)
    assert not target.exists()


def test_sqlite_backup_includes_committed_uncheckpointed_wal(tmp_path):
    path = tmp_path / "live.sqlite3"
    writer = sqlite3.connect(path)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("CREATE TABLE notes (value TEXT)")
        writer.execute("INSERT INTO notes VALUES ('Committed in WAL')")
        writer.commit()
        assert Path(str(path) + "-wal").stat().st_size > 0
        backup = create_backup(f"sqlite:///{path}", tmp_path / "snapshot.sqlite3")
        with sqlite3.connect(backup) as restored:
            assert restored.execute("SELECT value FROM notes").fetchall() == [("Committed in WAL",)]
    finally:
        writer.close()


def test_cli_uses_only_explicit_environment_variable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'source.sqlite3'}")
    try:
        bootstrap_database(engine)
    finally:
        engine.dispose()
    backup = tmp_path / "snapshot.sqlite3"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "db.backup",
            "create",
            "--url-env",
            "BACKUP_SOURCE_URL",
            "--file",
            str(backup),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "BACKUP_SOURCE_URL": str(engine.url),
            "DATABASE_URL": "postgresql://unused:private-password@invalid.example/personal",
        },
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert backup.exists()
    assert "private-password" not in result.stdout + result.stderr


@pytest.fixture
def postgres_databases():
    value = os.getenv("TEST_POSTGRES_URL")
    if not value:
        pytest.skip("Set TEST_POSTGRES_URL for native PostgreSQL backup acceptance")
    assert shutil.which("pg_dump") and shutil.which("pg_restore")
    admin = create_engine(value, isolation_level="AUTOCOMMIT")
    databases = ["backup_check_" + uuid4().hex for _ in range(2)]
    engines = []
    try:
        for name in databases:
            with admin.connect() as connection:
                connection.exec_driver_sql('CREATE DATABASE "' + name + '"')
            engines.append(create_engine(admin.url.set(database=name)))
        yield engines
    finally:
        for engine in engines:
            engine.dispose()
        for name in databases:
            with admin.connect() as connection:
                connection.exec_driver_sql('DROP DATABASE IF EXISTS "' + name + '" WITH (FORCE)')
        admin.dispose()


def test_postgres_native_backup_restores_records_constraints_and_sequences(
    postgres_databases, tmp_path
):
    source, restored = postgres_databases
    bootstrap_database(source, demo=True)
    before = snapshot(source)
    backup = create_backup(source.url, tmp_path / "snapshot.dump")
    assert snapshot(source) == before
    with pytest.raises(BackupError, match="empty public schema"):
        restore_backup(source.url, backup)
    restore_backup(restored.url, backup)
    assert snapshot(restored) == before
    manager = DataManager(engine=restored)
    assert manager.add_exercise("Chest Dip")
    with restored.connect() as connection:
        assert connection.execute(text("SELECT max(exercise_id) FROM exercises")).scalar_one() == 10
    assert snapshot(source) == before
