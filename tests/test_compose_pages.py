"""Exercise Compose's page, schema and persistence probes without requiring Docker."""

import json
from unittest.mock import patch

from sqlalchemy import create_engine

from data_loader import load_data
from db.bootstrap import bootstrap_database
from scripts.check_compose import CHECK_PAGES, SNAPSHOT, WRITE_RECORD


def test_compose_page_probe_covers_current_routes_and_analysis_tabs(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'compose-probe.sqlite3'}")
    bootstrap_database(engine, demo=True)
    load_data.clear()
    try:
        with patch("data_manager.get_engine", return_value=engine):
            exec(CHECK_PAGES, {})
    finally:
        load_data.clear()
        engine.dispose()


def test_compose_snapshot_tracks_current_schema_and_survives_reconnection(tmp_path, capsys):
    url = f"sqlite:///{tmp_path / 'compose-persistence.sqlite3'}"
    engine = create_engine(url)
    bootstrap_database(engine, demo=True)
    load_data.clear()

    def execute(code):
        exec(code, {})
        return json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    try:
        with patch("db.connection.get_engine", return_value=engine):
            initial = execute(SNAPSHOT)
        assert len(initial["counts"]) == 22
        assert "exercise_load_profiles" in initial["counts"]
        assert "workout_set_load_originals" in initial["counts"]
        with (
            patch("data_manager.get_engine", return_value=engine),
            patch("db.connection.get_engine", return_value=engine),
        ):
            written = execute(WRITE_RECORD + SNAPSHOT)
        assert written["counts"]["workout_sessions"] == initial["counts"]["workout_sessions"] + 1
        assert written["counts"]["workout_sets"] == initial["counts"]["workout_sets"] + 1
        engine.dispose()
        engine = create_engine(url)
        with patch("db.connection.get_engine", return_value=engine):
            assert execute(SNAPSHOT) == written
    finally:
        load_data.clear()
        engine.dispose()
