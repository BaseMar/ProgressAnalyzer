import streamlit as st
from core.data_manager import DataManager
from core.analytics import TrainingAnalytics
from core.services.kpi_service import KPIService
from core.ui.kpi_view import KPIView
from core.ui.charts_view import ChartsView
from core.ui.history_view import HistoryView
from core.styles.theme_manager import ThemeManager
from core.ui.footer_view import FooterView


def main():
    st.set_page_config(page_title="Gym Progress Dashboard", layout="wide")

    # --- STYL STRONY ---
    theme = ThemeManager()
    theme.apply_theme()

    st.title("Gym Progress Dashboard")

    # --- DANE ---
    data = DataManager()
    sets_df = data.load_sets()
    analytics = TrainingAnalytics(sets_df)
    kpi_service = KPIService(analytics)
    kpis = kpi_service.get_kpis()

    # --- PANEL BOCZNY ---
    st.sidebar.title("🏋️ Nawigacja")
    menu = st.sidebar.radio(
        "Wybierz sekcję:",
        ["Formularz", "Analiza ćwiczeń", "Analiza grup mięśniowych", "Pomiary ciała"])
    
    # --- KARTY KPI ---
    KPIView.display(kpis)

    # --- WYKRESY ---
    ChartsView.render(analytics)

    # --- HISTORIA TRENINGÓW ---
    HistoryView(sets_df).render()

    # --- STOPKA ---
    footer = FooterView()
    footer.render()

if __name__ == "__main__":
    main()
