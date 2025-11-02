from sqlalchemy import create_engine
import streamlit as st


@st.cache_resource
def get_engine():
    """ Return SQLAlchemy Engine object."""
    try:
        connection_string = (
            "mssql+pyodbc://DESKTOP-CGQ7P1E\\MSSQLSERVER04/GymProgressDB"
            "?driver=ODBC+Driver+17+for+SQL+Server"
            "&trusted_connection=yes"
        )
        engine = create_engine(connection_string, fast_executemany=True)
        print("Połączono z bazą danych (SQLAlchemy)")
        return engine
    except Exception as e:
        print("Błąd połączenia z bazą danych:", e)
        return None
