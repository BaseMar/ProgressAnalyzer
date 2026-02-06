from pathlib import Path
import pandas as pd
import streamlit as st

from data_loader import load_data

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


class StreamlitApp:
    """
    Main entry point for the Workout Progress Analyzer Streamlit application.

    This class orchestrates:
    - Page configuration
    - Data loading
    - Metric computation
    - View routing
    """

    def __init__(self) -> None:
        """Initialize and configure the Streamlit page."""
        self._configure_page()

    def _configure_page(self) -> None:
        """Configure global Streamlit page settings."""
        st.set_page_config(
            page_title="Workout Progress Analyzer",
            page_icon="💪",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        self._load_global_styles()

    def _load_data(self) -> tuple[dict | None, pd.DataFrame | None]:
        """Load raw datasets required by the application.
        Returns:
            tuple:
                Raw metrics input dictionary and sets dataframe"""
        try:
            return load_data()
        except Exception as exc:
            st.error(f"Failed to load data: {exc}")
            return None, None

    def run(self) -> None:
        """Execute the Streamlit application."""
        raw_input_data, sets_dataframe = self._load_data()
        
        if raw_input_data is None or sets_dataframe is None:
            st.stop()

        sidebar = SidebarView()
        selected_month = sidebar.render_filters(sets_dataframe)

        filtered_input, filtered_sets_dataframe = filter_data_by_month(raw_input_data, sets_dataframe, selected_month,)

        metrics = self._compute_metrics(filtered_input)

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
    
    def _load_global_styles(self) -> None:
        """Load global CSS styles used across the application."""
        css_path = Path(__file__).resolve().parent / "styles" / "main.css"

        if css_path.exists():
            with open(css_path, encoding="utf-8") as f:
                st.markdown(
                    f"<style>{f.read()}</style>",
                    unsafe_allow_html=True
                )
        else:
            st.error(f"CSS NOT FOUND: {css_path}")

    def _compute_metrics(self, input_data: dict) -> dict:
        """
        Compute all domain metrics used in the UI.

        Args:
            input_data: Preprocessed input data dictionary.

        Returns:
            Dictionary containing all computed metric groups.
        """
        return {
            "sessions": compute_session_metrics(input_data),
            "exercises": compute_exercise_metrics(input_data),
            "progress": compute_progress_metrics(input_data),
            "fatigue": compute_fatigue_metrics(input_data),
            "body": compute_body_metrics(input_data),
        }   


def main() -> None:
    """Application entry point."""
    StreamlitApp().run()


if __name__ == "__main__":
    main()
