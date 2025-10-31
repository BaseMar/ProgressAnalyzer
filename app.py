import streamlit as st
from core.data_manager import DataManager
from core.analytics import TrainingAnalytics
from core.services.kpi_service import KPIService

def main():
    st.set_page_config(page_title="Gym Progress Dashboard", layout="wide")

    st.title("🏋️‍♂️ Gym Progress Dashboard")

    data = DataManager()
    sets_df = data.load_sets()

    analytics = TrainingAnalytics(sets_df)
    kpi_service = KPIService(analytics)
    kpis = kpi_service.get_kpis()

    # --- KPI CARDS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Średnia intensywność", f"{kpis['avg_intensity']:.1f}", delta=f"{kpis['intensity_change']}%")
    col2.metric("Łączna objętość tygodniowa", f"{kpis['total_volume']:.0f}", delta=f"{kpis['volume_change']}%")
    col3.metric("Liczba sesji", kpis["sessions"])
    col4.metric("Wskaźnik progresu", "W budowie 🚧")


if __name__ == "__main__":
    main()
