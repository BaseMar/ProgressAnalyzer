"""The public entry point must stay isolated from personal configuration and caches."""

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from data_loader import load_data
from data_manager import DataManager
from db.connection import database_scope
from db.public_demo import create_demo_database

ROOT = Path(__file__).resolve().parents[1]
APP = """
from streamlit_app import run
from db.public_demo import session_demo_database
import streamlit as st
from uuid import uuid4
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
# AppTest uses one fixed context ID; model two real browser IDs explicitly.
get_script_run_ctx().session_id = st.session_state.setdefault('test_session_id', uuid4().hex)
run(demo=True)
database = session_demo_database()
st.session_state['sandbox'] = database
"""


@pytest.mark.parametrize("page", ["Overview", "Analysis", "Plan", "History"])
def test_public_entry_renders_without_resolving_personal_database(page, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://private:secret@invalid.example/personal")
    with patch("db.connection._get_database_url", side_effect=AssertionError("Personal URL read")):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
        app.session_state["nav_selected"] = page
        app.run()
        assert not app.exception and not app.error
        assert app.sidebar.button(key="reset_public_demo")
        assert "Fictional data" in app.info[0].value


def test_demo_sessions_keep_their_edits_and_reset_independently():
    first = AppTest.from_string(APP, default_timeout=30).run()
    second = AppTest.from_string(APP, default_timeout=30).run()
    assert not first.exception and not second.exception
    a, b = first.session_state["sandbox"], second.session_state["sandbox"]
    assert a.cache_key != b.cache_key
    with database_scope(a.engine, a.cache_key):
        assert DataManager().delete_session(1)
        first_count = len(load_data()[0].sessions)
    with database_scope(b.engine, b.cache_key):
        assert len(load_data()[0].sessions) == first_count + 1
    first.run()
    assert first.session_state["sandbox"] is a
    first.sidebar.button(key="reset_public_demo").click().run()
    assert not first.exception and not first.error
    reset = first.session_state["sandbox"]
    assert reset.cache_key != a.cache_key
    with database_scope(reset.engine, reset.cache_key):
        assert len(load_data()[0].sessions) == first_count + 1
    second.run()
    assert second.session_state["sandbox"] is b


def test_sandbox_inputs_cannot_reuse_another_database_cache():
    personal, demo = create_demo_database(), create_demo_database()
    try:
        with personal.engine.begin() as connection:
            connection.execute(text("UPDATE exercises SET exercise_name='Private exercise'"))
        with database_scope(personal.engine, personal.cache_key):
            assert {row.name for row in load_data()[0].exercises} == {"Private exercise"}
        with database_scope(demo.engine, demo.cache_key):
            assert "Private exercise" not in {row.name for row in load_data()[0].exercises}
    finally:
        personal.engine.dispose()
        demo.engine.dispose()
        load_data.clear()
