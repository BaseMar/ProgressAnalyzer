"""
Workout Progress Analyzer

A Streamlit-based analytics dashboard for monitoring strength training progress,
body composition changes, exercise performance, and training consistency.

Architecture:
  The application follows clean architecture with clear layer separation:
  
  1. Data Layer (data_manager.py, db/)
     - Database queries and persistence
     - Returns Pandas DataFrames
  
  2. Metrics Layer (metrics/)
     - Pure functions that compute KPIs from raw data
     - Modules: session_metrics, exercise_metrics, progress_metrics,
               fatigue_metrics, body_metrics
     - All calculations are stateless and testable
  
  3. Presentation Layer (ui/)
     - Streamlit view classes
     - Presentation-only, no business logic
     - Receive pre-computed metrics dictionaries
     - Handle styling and layout
  
DataFlow:
  Load Data → Compute Metrics → Render Views (one-way, no feedback loops)

Key Design Principles:
  - Views don't compute anything; all metrics pre-computed
  - Metrics are pure functions with no Streamlit dependencies
  - Type safety: structured data types throughout (MetricsInput, etc)
  - Single responsibility: each module has one clear concern
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import load_data
from metrics.input import MetricsInput

from metrics.body_metrics import compute_body_metrics
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.fatigue_metrics import compute_fatigue_metrics
from metrics.progress_metrics import compute_progress_metrics
from metrics.session_metrics import compute_session_metrics

from ui.sidebar_view import SidebarView
from ui.dashboard_view import DashboardView
from ui.exercise_view import ExerciseView
from ui.body_parts_view import BodyPartsView
from ui.analytics_view import AnalyticsView
from ui.body_metrics_view import BodyMetricsView
from ui.utils.data_filter import filter_data_by_month


@st.cache_data(ttl=300, show_spinner="Loading workout data…")
def _load_data_cached() -> tuple[MetricsInput, pd.DataFrame]:
    """Load and cache application data with a 5-minute TTL."""
    return load_data()

def _configure_page() -> None:
    """Configure Streamlit page settings (title, layout, sidebar state)."""
    st.set_page_config(
        page_title="Workout Progress Analyzer",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="expanded",
    )

def _load_global_styles() -> None:
    """Inject main.css into the Streamlit page."""
    css_path = Path(__file__).resolve().parent / "ui" / "styles" / "main.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.error(f"CSS NOT FOUND: {css_path}")

def _compute_metrics(input_data: MetricsInput) -> dict:
    """Compute all domain metrics from filtered input data.
    
    Args:
        input_data: MetricsInput with filtered session/exercise/body data
    
    Returns:
        Dictionary containing all computed metrics by domain:
        - sessions: Session-level metrics
        - exercises: Exercise-level metrics  
        - progress: Strength progress metrics
        - fatigue: Fatigue and recovery metrics
        - body: Body composition and measurement metrics
    """
    return {
        "sessions": compute_session_metrics(input_data),
        "exercises": compute_exercise_metrics(input_data),
        "progress": compute_progress_metrics(input_data),
        "fatigue": compute_fatigue_metrics(input_data),
        "body": compute_body_metrics(input_data),
    }

def main() -> None:
    """
    Application entry point orchestrating the complete data and view pipeline.

    Execution order on every Streamlit widget interaction or rerun:
      1. Load cached data            — database is queried once per TTL (300s)
      2. Render sidebar              — month filter and navigation controls
      3. Filter application data     — slice to selected month
      4. Compute all metrics         — process filtered data through metrics layer
      5. Render selected view        — display pre-computed metrics

    Architecture:
    - Data flows one direction: database → metrics engine → views
    - Views are stateless and presentation-only
    - All logic is in the metrics layer (metrics/*.py)
    """
    _load_global_styles()

    try:
        raw_input_data, sets_dataframe = _load_data_cached()
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")
        st.stop()

    sidebar = SidebarView()
    selected_month = sidebar.render_filters(sets_dataframe)

    filtered_input, filtered_sets_dataframe = filter_data_by_month(
        raw_input_data, sets_dataframe, selected_month,
    )

    metrics = _compute_metrics(filtered_input)

    selected_page = sidebar.render_navigation()

    views = {
        "Main Dashboard": DashboardView(metrics, filtered_sets_dataframe),
        "Exercises": ExerciseView(metrics["exercises"], filtered_sets_dataframe),
        "Body Parts": BodyPartsView(metrics["exercises"]),
        "Analytics": AnalyticsView(metrics),
        "Body Metrics": BodyMetricsView(metrics["body"]),
    }

    views[selected_page].render()
    sidebar.render_upload()

    # personal data disclaimer footer
    st.markdown('<div class="app-footer">All data shown are my personal workout and body measurements, used solely for the purposes of this project.</div>', unsafe_allow_html=True,)

_configure_page()


if __name__ == "__main__":
    main()