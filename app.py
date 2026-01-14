import streamlit as st
from core.config import AppConfig
from core.styles.theme_manager import ThemeManager
from core.ui.dashboard_mainpage.dashboard_view import DashboardView
from data_loader import load_data


class GymDashboardApp:
    """Main application class for Gym Progress Dashboard."""

    def __init__(self):
        self.config = AppConfig()
        self.theme = ThemeManager()

        self._init_session_state()
        self._init_page_config()

    def _init_session_state(self) -> None:
        """Initialize Streamlit session state variables."""
        st.session_state.setdefault("current_section", "Dashboard")
        st.session_state.setdefault("current_week_idx", 0)

    def _init_page_config(self) -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title=self.config.APP_TITLE,
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
        self.theme.apply_theme()
        metrics, sets_df = self._load_dependencies()
        dashboard = DashboardView(metrics=metrics, sets_df=sets_df, theme=self.theme)
        dashboard.render()


def main():
    app = GymDashboardApp()
    app.run()


if __name__ == "__main__":
    main()
