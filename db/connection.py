import logging
import os

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()

logger = logging.getLogger(__name__)


@st.cache_resource
def get_engine() -> Engine:
    """Create and cache a SQLAlchemy Engine using the DATABASE_URL environment variable.

    This function is cached by Streamlit to reuse the engine instance across reruns.
    Raises RuntimeError if `DATABASE_URL` is not configured.
    """

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set in environment")
        raise RuntimeError("DATABASE_URL is not set")

    try:
        engine = create_engine(database_url, fast_executemany=True)
        logger.info("Connected to database (SQLAlchemy)")
        return engine
    except Exception as ex:
        logger.exception("Error creating SQLAlchemy engine")
        raise
