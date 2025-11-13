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
        
        # --- Pobierz dane ---
        df = self.analytics.df_sets.copy()
        if df.empty:
            st.info("Brak danych do analizy ćwiczeń.")
            return
        exercises = sorted(df["ExerciseName"].unique().tolist())

        # --- Wybór ćwiczenia ---
        selected_exercise = st.selectbox("Wybierz ćwiczenie", exercises)
        df_exercise = df[df["ExerciseName"] == selected_exercise].copy()
        if df_exercise.empty:
            st.warning("Brak danych dla wybranego ćwiczenia.")
            return
        
        # --- Agregacja ---
        df_summary = (
            df_exercise.groupby("SessionDate")
            .agg(SeriesCount=("SetNumber", "count"), TotalReps=("Repetitions", "sum"), AvgWeight=("Weight", "mean"), Volume=("Volume", "sum"),).reset_index().sort_values("SessionDate"))
        df_summary["SessionDate"] = pd.to_datetime(df_summary["SessionDate"]).dt.date
        
        # --- Przetwarzanie danych ---
        ## Szacowany 1RM (Wzór Epleya)
        
        df_exercise["Est1RM"] = df_exercise["Weight"] * (1 + df_exercise["Repetitions"] / 30)
        df_exercise["TotalVolume"] = df_exercise["Repetitions"] * df_exercise["Weight"]


        df_summary["AvgWeight"] = df_summary["AvgWeight"].round(1)
        df_summary["Volume"] = df_summary["Volume"].round(1)

        # Grupowanie po sesjach (uśrednianie)
        session_summary = (
            df_exercise.groupby("SessionDate")
            .agg({
                "Est1RM": "max",
                "TotalVolume": "sum",
                "Weight": "mean"
            })
            .reset_index()
            .sort_values("SessionDate")
        )
        
        # --- KPI sekcja ---
        latest_1rm = session_summary["Est1RM"].iloc[-1]
        start_1rm = session_summary["Est1RM"].iloc[0]
        progress = ((latest_1rm - start_1rm) / start_1rm * 100) if start_1rm > 0 else 0
        avg_weight = session_summary["Weight"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Szacowany 1RM (kg)", f"{latest_1rm:.1f}")
        col2.metric("Progres od początku", f"{progress:+.1f}%")
        col3.metric("Średni ciężar roboczy (kg)", f"{avg_weight:.1f}")

        st.divider()

        # --- Wykres trendu 1RM ---
        st.subheader("Trend 1RM w czasie")
        fig_rm = px.line(
            session_summary,
            x="SessionDate",
            y="Est1RM",
            markers=True,
            title=f"Szacowany 1RM dla: {selected_exercise}",
            color_discrete_sequence=[self.theme.colors.accent]
        )
        fig_rm.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.theme.colors.text,
            title_font_size=16
        )
        st.plotly_chart(fig_rm, width="stretch")

        # --- Wykres objętości ---
        st.subheader("Objętość treningowa w czasie")
        fig_vol = px.bar(
            session_summary,
            x="SessionDate",
            y="TotalVolume",
            title="Objętość (Powtózenia × Ciężar)",
            color_discrete_sequence=[self.theme.colors.accent_light]
        )
        fig_vol.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.theme.colors.text,
            title_font_size=16
        )
        st.plotly_chart(fig_vol, width="stretch")

        # --- Historia sesji ---
        st.subheader(f"Historia ćwiczenia: {selected_exercise}")
        st.dataframe(
            df_summary,
            hide_index=True,
            use_container_width=True
        )

    def _render_muscle_group_analysis(self):
        """Render muscle group analysis section"""
        st.header("💪 Analiza grup mięśniowych")
        self.charts_view.render_muscle_group_analysis(self.analytics)
        st.info("Sekcja Analiza grup mięśniowych - w przygotowaniu")
    
    def _render_body_measurements(self):
        """Render body measurements section"""
        st.header("📏 Pomiary ciała")
        st.info("Sekcja pomiarów ciała - w przygotowaniu")