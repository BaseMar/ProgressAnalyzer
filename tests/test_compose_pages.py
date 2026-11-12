"""Run the Compose UI probe locally so navigation changes cannot leave it stale."""

from unittest.mock import patch

from sqlalchemy import create_engine

from data_loader import load_data
from db.bootstrap import bootstrap_database
from scripts.check_compose import CHECK_PAGES


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
