import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

logger = logging.getLogger(__name__)

@st.cache_resource
def get_engine() -> Engine:
    """Tworzy i cache'uje SQLAlchemy Engine. Oczekuje zmiennej środowiskowej DATABASE_URL"""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("Brak DATABASE_URL w środowisku")
        raise RuntimeError("DATABASE_URL is not set")

    try:
        engine = create_engine(database_url, fast_executemany=True)
        logger.info("Połączono z bazą danych (SQLAlchemy)")
        return engine
    except Exception as ex:
        logger.exception("Błąd przy tworzeniu silnika SQLAlchemy")
        raise
