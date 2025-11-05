import streamlit as st
from typing import Optional
from ..sidebar_view import SidebarView
from .kpi_view import KPIView
from .charts_view import ChartsView
from .history_view import HistoryView
from ..footer_view import FooterView
from ...styles.theme_manager import ThemeManager
from ..forms.exercise_form import ExerciseFormView
from ..forms.workout_session_form import SessionFormView
from ..forms.body_measurement_form import BodyMeasurementsFormView
from ..forms.body_composition_form import BodyCompositionFormView

class DashboardView:
    """Main dashboard orchestrator"""
    
    def __init__(self, sets_df, analytics, kpi_service, theme: ThemeManager):
        self.sets_df = sets_df
        self.analytics = analytics
        self.kpi_service = kpi_service
        self.theme = theme
        
        # Initialize views
        self.sidebar_view = SidebarView()
        self.kpi_view = KPIView(theme)
        self.charts_view = ChartsView(theme)
        self.history_view = HistoryView(sets_df, theme)
        self.footer_view = FooterView(theme)
    
    def render(self):
        """Render the complete dashboard"""
        # Header
        st.title("Gym Progress Dashboard")
        
        # Sidebar navigation
        selected_section = self.sidebar_view.render()
        
        # Main content based on selection
        if selected_section == "Dashboard":
            self._render_main_dashboard()
        elif selected_section == "Formularz":
            self._render_form_section()
        elif selected_section == "Analiza ćwiczeń":
            self._render_exercise_analysis()
        elif selected_section == "Analiza grup mięśniowych":
            self._render_muscle_group_analysis()
        elif selected_section == "Pomiary ciała":
            self._render_body_measurements()
        
        # Footer
        self.footer_view.render()
    
    def _render_main_dashboard(self):
        """Render main dashboard content"""
        # KPI Cards
        kpis = self.kpi_service.get_kpis()
        self.kpi_view.display(kpis)
        
        # Charts
        self.charts_view.render(self.analytics)
        
        # history
        st.divider()
        self.history_view.render()
    
    def _render_form_section(self):
        """Render form section"""
        tabs = st.tabs(["➕ Ćwiczenia", "🏋️‍♂️ Sesje treningowe", "📏 Pomiary ciała", "⚖️ Skład ciała"])

        with tabs[0]:
            ExerciseFormView().render()
        with tabs[1]:
            SessionFormView().render()
        with tabs[2]:
            BodyMeasurementsFormView().render()
        with tabs[3]:
            BodyCompositionFormView().render()
    
    def _render_exercise_analysis(self):
        """Render exercise analysis section"""
        st.header("🏋️ Analiza ćwiczeń")
        self.charts_view.render_exercise_analysis(self.analytics)
        st.info("Sekcja analiza ćwiczeń - w przygotowaniu")
    
    def _render_muscle_group_analysis(self):
        """Render muscle group analysis section"""
        st.header("💪 Analiza grup mięśniowych")
        self.charts_view.render_muscle_group_analysis(self.analytics)
        st.info("Sekcja Analiza grup mięśniowych - w przygotowaniu")
    
    def _render_body_measurements(self):
        """Render body measurements section"""
        st.header("📏 Pomiary ciała")
        st.info("Sekcja pomiarów ciała - w przygotowaniu")