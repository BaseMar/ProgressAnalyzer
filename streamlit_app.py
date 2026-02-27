from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import load_data as _load_data_raw

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
def _load_data_cached() -> tuple[dict, pd.DataFrame]:
    return _load_data_raw()

def _configure_page() -> None:
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

def _compute_metrics(input_data: dict) -> dict:
    """Compute all domain metrics from filtered input data."""
    return {
        "sessions": compute_session_metrics(input_data),
        "exercises": compute_exercise_metrics(input_data),
        "progress": compute_progress_metrics(input_data),
        "fatigue": compute_fatigue_metrics(input_data),
        "body": compute_body_metrics(input_data),
    }

def main() -> None:
    """
    Application entry point.

    Execution order on every rerun:
      1. _load_data_cached()      — served from cache, no DB call
      2. sidebar.render_filters() — reads selected_month from session state
      3. filter_data_by_month()   — slices cached data by the selected filter
      4. _compute_metrics()       — recomputes on filtered data
      5. selected view.render()   — renders with fresh metrics
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

_configure_page()


if __name__ == "__main__":
    main()