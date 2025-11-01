import streamlit as st
from pathlib import Path
import sys

# Add core directory to path
sys.path.append(str(Path(__file__).parent))

from core.data_manager import DataManager
from core.analytics import TrainingAnalytics
from core.services.kpi_service import KPIService
from core.ui.dashboard_view import DashboardView
from core.styles.theme_manager import ThemeManager, ColorPalette
from core.config import AppConfig

class GymDashboardApp:
    """Main application class for Gym Progress Dashboard"""
    
    def __init__(self):
        self.config = AppConfig()
        self.theme = ThemeManager()
        self._initialize_session_state()
        self._setup_page_config()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'current_section' not in st.session_state:
            st.session_state.current_section = "Dashboard"
        if 'current_week_idx' not in st.session_state:
            st.session_state.current_week_idx = 0
    
    def _setup_page_config(self):
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title=self.config.APP_TITLE,
            page_icon="💪",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def _load_data(self):
        """Load and prepare data"""
        try:
            data_manager = DataManager()
            sets_df = data_manager.load_sets()
            analytics = TrainingAnalytics(sets_df)
            kpi_service = KPIService(analytics)
            return sets_df, analytics, kpi_service
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None, None, None
    
    def run(self):
        """Main application entry point"""
        # Apply theme
        self.theme.apply_theme()
        
        # Load data
        sets_df, analytics, kpi_service = self._load_data()
        
        if analytics is None:
            st.error("Failed to load data. Please check your data source.")
            return
        
        # Initialize dashboard view
        dashboard = DashboardView(sets_df, analytics, kpi_service, self.theme)
        
        # Render application
        dashboard.render()

def main():
    """Application entry point"""
    app = GymDashboardApp()
    app.run()

if __name__ == "__main__":
    main()