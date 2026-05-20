import logging
import os

import streamlit as st
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

env_path = find_dotenv(usecwd=True)
load_dotenv(env_path or None)

logger = logging.getLogger(__name__)


def _get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    try:
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


@st.cache_resource
def get_engine() -> Engine:
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
        logger.info("Connected to database (SQLAlchemy)")
        return engine
    except Exception as ex:
        logger.exception("Error creating SQLAlchemy engine")
        raise
