import pandas as pd
import streamlit as st
from metrics.body_metrics import compute_body_metrics
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.fatigue_metrics import compute_fatigue_metrics
from metrics.progress_metrics import compute_progress_metrics
from metrics.session_metrics import compute_session_metrics
from ui.dashboard_view import DashboardView
from data_loader import load_data
from ui.exercise_view import ExerciseView
from ui.body_parts_view import BodyPartsView
from ui.utils.data_filter import filter_data_by_month
from ui.sidebar_view import SidebarView
from ui.analytics_view import AnalyticsView


class GymDashboardApp:
    """Main application class for Gym Progress Dashboard."""

    def __init__(self):
        self._init_page_config()

    def _init_page_config(self) -> None:
        """Configure Streamlit page settings."""
        
        st.set_page_config(
            page_title="Gym Progress Dashboard",
            page_icon="💪",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def _load_dependencies(self) -> tuple[dict, pd.DataFrame]:
        """Load necessary data dependencies."""

        try:
            return load_data()
        except Exception as exc:
            st.error(f"Failed to load data: {exc}")
            return None, None, None

    def sidebar_filters(self, sets_df: pd.DataFrame) -> str:
        """
        Render sidebar filters and return selected filter values.

        Currently supports:
        - Monthly time filter (YYYY-MM)

        Parameters
        ----------
        sets_df : pd.DataFrame
            DataFrame containing set-level data with a SessionDate column.

        Returns
        -------
        str
            Selected month in 'YYYY-MM' format.
        """
        st.sidebar.header("Filters")

        if sets_df is None or sets_df.empty:
            st.sidebar.info("No data available for filtering.")
            return None

        # Ensure datetime type
        sets_df = sets_df.copy()
        sets_df["SessionDate"] = pd.to_datetime(sets_df["SessionDate"])

        available_months = (sets_df["SessionDate"].dt.to_period("M").astype(str).sort_values().unique())
        selected_month = st.sidebar.selectbox("Select month",options=available_months,index=len(available_months) - 1)

        return selected_month

    def run(self) -> None:
        """Main application entry point."""
        metrics_input, sets_df = self._load_dependencies()

        sidebar = SidebarView()

        # --- Sidebar ---
        selected_month = sidebar.render_filters(sets_df)

        # --- Filtering ---
        filtered_input, filtered_sets_df = filter_data_by_month(metrics_input, sets_df, selected_month,)

        # --- Metrics recomputation ---
        metrics = {
            "sessions": compute_session_metrics(filtered_input),
            "exercises": compute_exercise_metrics(filtered_input),
            "progress": compute_progress_metrics(filtered_input),
            "fatigue": compute_fatigue_metrics(filtered_input),
            "body": compute_body_metrics(filtered_input),
        }

        # --- Views ---
        dashboard_view = DashboardView(metrics, filtered_sets_df)
        exercises_view = ExerciseView(metrics["exercises"], filtered_sets_df)
        body_parts_view = BodyPartsView(metrics["exercises"])
        analytics_view = AnalyticsView(metrics)

        # --- Navigation ---
        section = sidebar.render_navigation()

        if section == "Main Dashboard":
            dashboard_view.render()
        elif section == "Exercises":
            exercises_view.render()
        elif section == "Body Parts":
            body_parts_view.render()
        elif section == "Analytics":
            analytics_view.render()

    # --- Sidebar Upload ---
        sidebar.render_upload()


def main():
    app = GymDashboardApp()
    app.run()


if __name__ == "__main__":
    main()
