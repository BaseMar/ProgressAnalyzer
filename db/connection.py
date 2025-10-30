import pyodbc
import pandas as pd
import streamlit as st

import pyodbc

def get_connection():
    conn_str = (
        "Driver={SQL Server};"
        r"Server=DESKTOP-CGQ7P1E\MSSQLSERVER04;"
        "Database=GymProgressDB;"
        "Trusted_Connection=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str)
        print("Połączono z bazą danych")
        return conn
    except Exception as e:
        print("Błąd połączenia z bazą danych:")
        print(e)
        return None


def run_query(query):
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    df = pd.read_sql(query, conn)
    conn.close()
    return df
