import streamlit as st
import pandas as pd
import plotly.express as px
from db.queries import (get_workout_sessions, get_all_sets, get_volume_by_bodypart,)
from components import parser


# --- CONFIG ---
st.set_page_config(page_title="Gym Progress Dashboard", page_icon="💪", layout="wide")

# --- SIDEBAR ---
st.sidebar.title("Menu")
menu = st.sidebar.radio( "Wybierz widok:", ["Dashboard ogólny", "Ćwiczenia", "Pomiary"])

st.sidebar.divider()
st.sidebar.header("Import danych treningowych")
uploaded_file = st.sidebar.file_uploader("📤 Wgraj plik treningu (.txt)", type=["txt"])

test_mode = st.sidebar.checkbox("Tryb testowy (bez zapisu)", value=True)

if uploaded_file is not None:
    if st.sidebar.button("Pokaż podgląd danych"):
        df_preview = parser.preview_training_file(uploaded_file)

        if not df_preview.empty:
            st.subheader("Podgląd rozpoznanych danych:")
            st.dataframe(df_preview)

            if st.button("Zapisz dane" if not test_mode else "Przetestuj parser"):
                parser.save_training_to_db(df_preview, test_mode=test_mode)
        else:
            st.info("Nie znaleziono danych do wyświetlenia lub plik był niepoprawny.")
            
if st.sidebar.button("Resetuj bazę (dev)"):
    st.warning("Ta funkcja będzie dodana później")

st.sidebar.divider()
st.sidebar.caption("Autor: Martino | 2025")

# --- DASHBOARD GŁÓWNY ---
if menu == "Dashboard ogólny":
    st.title("Dashboard ogólny - analiza treningów")

    sessions_df = get_workout_sessions()
    sets_df = get_all_sets()
    volume_df = get_volume_by_bodypart()

    if sessions_df.empty or sets_df.empty:
        st.warning("Brak danych w bazie. Wgraj trening lub dodaj dane.")
    else:
        # --- KPI / Statystyki ---
        total_volume = sets_df["Volume"].sum()
        total_sessions = sessions_df["SessionID"].nunique()
        total_exercises = sets_df["ExerciseName"].nunique()
        avg_intensity = round(sets_df["Weight"].mean(), 1)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Łączna objętość", f"{total_volume:.0f} kg")
        col2.metric("Sesje treningowe", total_sessions)
        col3.metric("Ćwiczeń wykonanych", total_exercises)
        col4.metric("Średnia intensywność", f"{avg_intensity} kg")

        st.markdown("---")

# --- ĆWICZENIA ---
elif menu == "Ćwiczenia":
    st.title("Analiza progresu dla ćwiczeń")
    st.info("Ta sekcja będzie gotowa w kolejnym kroku – tu zobaczysz progres siłowy, 1RM i objętość dla wybranego ćwiczenia.")

# --- POMIARY ---
elif menu == "Pomiary":
    st.title("Analiza pomiarów ciała")
    st.info("Sekcja w przygotowaniu – integracja z Body Measurements i Body Composition już wkrótce.")
