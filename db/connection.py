import pyodbc
import pandas as pd
import streamlit as st

def get_connection():
    try:
        conn = pyodbc.connect(
    r"Driver={ODBC Driver 17 for SQL Server};"
    r"Server=DESKTOP-CGQ7P1E\MSSQLSERVER04;"
    r"Database=GymDB;"
    r"Trusted_Connection=yes;"
)

        return conn
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return None

def run_query(query):
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    df = pd.read_sql(query, conn)
    conn.close()
    return df
