import streamlit as st
from ui.dashboard_view import DashboardView
from data_loader import load_data
from ui.exercise_view import ExerciseView


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

    def _load_dependencies(self):
        try:
            return load_data()
        except Exception as exc:
            st.error(f"Failed to load data: {exc}")
            return None, None, None

    def run(self) -> None:
        """Main application entry point."""
        metrics, sets_df = self._load_dependencies()
        
        # inicjalizacja widoków
        dashboard_view = DashboardView(metrics, sets_df)
        exercises_view = ExerciseView(metrics["exercises"], sets_df)

        # sidebar
        section = st.sidebar.radio("Choose section",["Main Dashboard", "Exercises"])

        # renderowanie wybranej sekcji
        if section == "Main Dashboard":
            dashboard_view.render()
        elif section == "Exercises":
            exercises_view.render()


def main():
    app = GymDashboardApp()
    app.run()


if __name__ == "__main__":
    main()
