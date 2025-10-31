import streamlit as st
from core.data_manager import DataManager
from core.analytics import TrainingAnalytics
from core.services.kpi_service import KPIService
from core.ui.kpi_view import KPIView
from core.ui.charts_view import ChartsView
from core.ui.history_view import HistoryView
from core.styles.theme_manager import ThemeManager


def main():
    st.set_page_config(page_title="Gym Progress Dashboard", layout="wide")

    # 🔹 Ustawienia stylu
    theme = ThemeManager()
    theme.apply_theme()

    st.title("Gym Progress Dashboard")

    data = DataManager()
    sets_df = data.load_sets()

    analytics = TrainingAnalytics(sets_df)
    kpi_service = KPIService(analytics)
    kpis = kpi_service.get_kpis()

    # --- KPI CARDS ---
    KPIView.display(kpis)

    # --- CHARTS VIEW ---
    ChartsView.render(analytics)

    # --- Historia treningów ---
    HistoryView(sets_df).render()

if __name__ == "__main__":
    main()
