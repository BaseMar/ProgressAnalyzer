import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar

import streamlit as st
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from db.read_cache import install_read_invalidation

logger = logging.getLogger(__name__)
_database_scope = ContextVar("application_database", default=None)


@contextmanager
def database_scope(engine, cache_key):
    """Bind demo reads and writes to one engine without changing process settings."""
    token = _database_scope.set((engine, cache_key))
    try:
        yield
    finally:
        _database_scope.reset(token)


def database_cache_key():
    scope = _database_scope.get()
    return scope[1] if scope is not None else "personal"


def get_engine() -> Engine:
    """Use the explicit demo scope or the configured personal database."""
    scope = _database_scope.get()
    return scope[0] if scope is not None else _get_personal_engine()


def _get_database_url() -> str | None:
    env_path = find_dotenv(usecwd=True)
    load_dotenv(env_path or None)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    try:
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


@st.cache_resource
def _get_personal_engine() -> Engine:
    """Create and cache a SQLAlchemy Engine using the DATABASE_URL environment variable.

    This function is cached by Streamlit to reuse the engine instance across reruns.
    Raises RuntimeError if `DATABASE_URL` is not configured.
    """

    database_url = _get_database_url()
    if not database_url:
        logger.error("DATABASE_URL not set")
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your local .env file, "
            "as an environment variable, or in Streamlit secrets."
        )

    try:
        engine = create_engine(database_url)
        if engine.dialect.name == "sqlite":
            event.listen(engine, "connect", _sqlite_foreign_keys)
        install_read_invalidation(engine)
        logger.info("Connected to database (SQLAlchemy)")
        return engine
    except Exception:
        logger.exception("Error creating SQLAlchemy engine")
        raise


def _sqlite_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


get_engine.clear = _get_personal_engine.clear
