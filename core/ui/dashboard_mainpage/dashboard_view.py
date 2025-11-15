import streamlit as st
from typing import Optional
from ..sidebar_view import SidebarView
from .kpi_view import KPIView
from ..charts_view import ChartsView
from .history_view import HistoryView
from ..footer_view import FooterView
from ...styles.theme_manager import ThemeManager
from ..forms.exercise_form import ExerciseFormView
from ..forms.workout_session_form import SessionFormView
from ..forms.body_measurement_form import BodyMeasurementsFormView
from ..forms.body_composition_form import BodyCompositionFormView
from core.analytics.analytics_exercise import ExerciseAnalytics

import plotly.express as px
import numpy as np
import pandas as pd

class DashboardView:
    """Main dashboard orchestrator"""
    
    def __init__(self, sets_df, analytics, kpi_service, theme: ThemeManager):
        self.sets_df = sets_df
        self.analytics = analytics
        self.kpi_service = kpi_service
        self.theme = theme
        self.exercise_analytics = ExerciseAnalytics(self.analytics.df_sets)
        
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
        st.header("Analiza ćwiczeń")

        # --- Selectbox ---
        exercises = self.exercise_analytics.list_exercises()
        selected = st.selectbox("Wybierz ćwiczenie", exercises)

        df_ex = self.exercise_analytics.filter_exercise(selected)
        if df_ex.empty:
            st.warning("Brak danych dla wybranego ćwiczenia.")
            return

        session_summary = self.exercise_analytics.compute_session_summary(df_ex)
        kpis = self.exercise_analytics.compute_kpis(session_summary)
        df_history = self.exercise_analytics.compute_history_table(df_ex)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- KPI ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.html(self.theme.create_kpi_card(title="Szacowany 1RM", value=f"{kpis['latest_1rm']:.1f} kg").strip())

        with col2:
            st.html(self.theme.create_kpi_card(title="Progress od startu", value=f"{kpis['progress']:+.1f}%").strip())

        with col3:
            st.html(self.theme.create_kpi_card(title="Średni roboczy ciężar",value=f"{kpis['avg_weight']:.1f} kg").strip())

        st.markdown("<hr>", unsafe_allow_html=True)

        # ------ Charts side-by-side ------
        col_left, col_right = st.columns(2)

        with col_left:
            chart_container = st.container()
            with chart_container:
                self.charts_view.render_exercise_1rm_chart(session_summary, selected)

        with col_right:
            chart_container = st.container()
            with chart_container:
                self.charts_view.render_exercise_volume_chart(session_summary, selected)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ------ TABLE ------
        st.subheader(f"Historia ćwiczenia: {selected}")
        st.dataframe(df_history, hide_index=True, use_container_width=True)
    
    def _render_muscle_group_analysis(self):
        """Render muscle group analysis section"""
        st.header("💪 Analiza grup mięśniowych")
        self.charts_view.render_muscle_group_analysis(self.analytics)
        st.info("Sekcja Analiza grup mięśniowych - w przygotowaniu")
    
    def _render_body_measurements(self):
        """Render body measurements section"""
        st.header("📏 Pomiary ciała")
        st.info("Sekcja pomiarów ciała - w przygotowaniu")

    def _render_exercise_kpis(self, session_summary):
        latest_1rm = session_summary["Est1RM"].iloc[-1]
        start_1rm = session_summary["Est1RM"].iloc[0]
        progress = ((latest_1rm - start_1rm) / start_1rm * 100) if start_1rm > 0 else 0
        avg_weight = session_summary["Weight"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Szacowany 1RM", f"{latest_1rm:.1f} kg")
        col2.metric("Progres", f"{progress:+.1f}%")
        col3.metric("Średni ciężar roboczy", f"{avg_weight:.1f} kg")

    def _render_exercise_history(self, df_history, exercise_name):
        st.subheader(f"Historia ćwiczenia: {exercise_name}")
        st.dataframe(df_history, hide_index=True, use_container_width=True)