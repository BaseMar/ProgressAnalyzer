import streamlit as st
from db.connection import get_connection
from db import queries
from components import parser

from components import kpis, charts, tables

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Gym Progress Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Boczna nawigacja ---
st.sidebar.title("Gym Progress Dashboard")

page = st.sidebar.radio(
    "Nawigacja",
    ["Dashboard", "Exercise Analysis", "Muscle Group Analysis", "Body Metrics"],
)

# --- Globalne filtry ---
st.sidebar.markdown("### Filtry globalne")
date_from = st.sidebar.date_input("Od daty")
date_to = st.sidebar.date_input("Do daty")
exercise_filter = st.sidebar.text_input("Filtr ćwiczenia")
muscle_filter = st.sidebar.text_input("Filtr partii mięśniowej")

st.sidebar.divider()
st.sidebar.markdown("### Akcje")

# --- Wgranie pliku txt ---
st.sidebar.header("Import danych treningowych")
uploaded_file = st.sidebar.file_uploader("📤 Wgraj plik treningu (.txt)", type=["txt"])

test_mode = st.sidebar.checkbox("Tryb testowy (bez zapisu)", value=True)

if uploaded_file is not None:
    if st.sidebar.button("Pokaż podgląd danych"):
        df_preview = parser.preview_training_file(uploaded_file)

        if not df_preview.empty:
            st.subheader("Podgląd rozpoznanych danych:")
            st.dataframe(df_preview)

            # przycisk zapisu z obsługą trybu testowego
            if st.button("Zapisz dane" if not test_mode else "🧪 Przetestuj parser"):
                parser.save_training_to_db(df_preview, test_mode=test_mode)
        else:
            st.info("Nie znaleziono danych do wyświetlenia lub plik był niepoprawny.")
            
if st.sidebar.button("Resetuj bazę (dev)"):
    st.warning("Ta funkcja będzie dodana później")

# --- Logika strony ---
if page == "Dashboard":
    st.header("Dashboard – Podsumowanie treningów")

    # Tymczasowe dane testowe
    col1, col2, col3 = st.columns(3)
    with col1:
        kpis.metric_card("Total Volume", "12500 kg", "↑ 8% vs last week")
    with col2:
        kpis.metric_card("Avg Intensity", "72%", "↔ steady")
    with col3:
        kpis.metric_card("Sessions", "14", "↑ 2")

    st.divider()
    st.subheader("Trend objętości treningowej")
    charts.placeholder_chart()

elif page == "Exercise Analysis":
    st.header("Analiza ćwiczenia")
    charts.placeholder_chart()
    tables.placeholder_table()

elif page == "Muscle Group Analysis":
    st.header("Analiza grup mięśniowych")
    charts.placeholder_chart()

elif page == "Body Metrics":
    st.header("Body Composition & Measurements")
    charts.placeholder_chart()
