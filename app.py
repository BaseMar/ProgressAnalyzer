import streamlit as st
from ui.dashboard_mainpage.dashboard_view import DashboardView
from data_loader import load_data


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
        dashboard = DashboardView(metrics=metrics, sets_df=sets_df)
        dashboard.render()


def main():
    app = GymDashboardApp()
    app.run()


if __name__ == "__main__":
    main()
