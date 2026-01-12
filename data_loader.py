import streamlit as st
from core.analytics.training import TrainingAnalytics
from core.data_manager import DataManager
from core.services.kpi_service import KPIService


@st.cache_data
def load_data():
    """Load and prepare data for the dashboard."""
    data_manager = DataManager()
    sets_df = data_manager.load_sets()

    analytics = TrainingAnalytics(sets_df)
    kpi_service = KPIService(analytics)

    return sets_df, analytics, kpi_service
