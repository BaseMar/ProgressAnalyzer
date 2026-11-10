"""Give each browser session an ephemeral, generated SQLite training sandbox."""

from dataclasses import dataclass
from uuid import uuid4

import streamlit as st
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from db.bootstrap import bootstrap_database
from db.connection import _sqlite_foreign_keys
from db.read_cache import install_read_invalidation


@dataclass(frozen=True)
class DemoDatabase:
    engine: Engine
    cache_key: str


def create_demo_database():
    """Seed constants in memory; never resolve environment URLs or app secrets."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _sqlite_foreign_keys)
    try:
        bootstrap_database(engine, demo=True)
        install_read_invalidation(engine)
        return DemoDatabase(engine, uuid4().hex)
    except BaseException:
        engine.dispose()
        raise


@st.cache_resource(scope="session", on_release=lambda database: database.engine.dispose())
def session_demo_database():
    """Keep edits across reruns and release the database when the session expires."""
    return create_demo_database()
