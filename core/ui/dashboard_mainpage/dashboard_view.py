import streamlit as st
from typing import Any, Optional

from core.analytics.exercise import ExerciseAnalytics
from core.analytics.muscles import MuscleAnalytics

from ...styles.theme_manager import ThemeManager
from ..charts_view import ChartsView
from ..footer_view import FooterView
from ..forms.body_composition_form import BodyCompositionFormView
from ..forms.body_measurement_form import BodyMeasurementsFormView
from ..forms.exercise_form import ExerciseFormView
from ..forms.workout_session_form import SessionFormView
from ..sidebar_view import SidebarView
from .history_view import HistoryView
from .kpi_view import KPIView
from ...services.dashboard_service import DashboardService


class DashboardView:
    """Main dashboard orchestrator"""

    def __init__(
        self,
        sets_df: Any,
        analytics: Any,
        kpi_service: Any,
        theme: ThemeManager,
    ) -> None:
        self.sets_df: Any = sets_df
        self.analytics: Any = analytics
        self.kpi_service: Any = kpi_service
        self.theme: ThemeManager = theme
        self.exercise_analytics: ExerciseAnalytics = ExerciseAnalytics(
            self.analytics.df_sets
        )
        self.muscles: MuscleAnalytics = MuscleAnalytics(self.analytics.df_sets)

        # Service layer to keep UI thin
        self.dashboard_service: DashboardService = DashboardService(self.analytics, self.kpi_service)

        # Initialize views
        self.sidebar_view: SidebarView = SidebarView()
        self.kpi_view: KPIView = KPIView(theme)
        self.charts_view: ChartsView = ChartsView(theme)
        self.history_view: HistoryView = HistoryView(sets_df, theme)
        self.footer_view: FooterView = FooterView(theme)

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
        kpis = self.dashboard_service.get_dashboard_kpis()
        kpi_cards = [
            {
                "title": "Średnia intensywność",
                "value": f"{kpis['avg_intensity']:.1f} %",
                "delta": f"Δ {kpis['intensity_change']}%",
            },
            {
                "title": "Łączna objętość tygodniowa",
                "value": f"{kpis['total_volume']:,.0f}".replace(",", " ") + " kg",
                "delta": f"Δ {kpis['volume_change']}%",
            },
            {"title": "Liczba sesji", "value": str(kpis["sessions"]), "delta": None},
            {
                "title": "Śr. liczba serii / sesję",
                "value": f"{kpis['avg_sets_per_session']:.1f}",
                "delta": f"Δ {kpis['sets_change']}%",
            },
        ]
        self.kpi_view.display(kpi_cards)

        # Charts
        self.charts_view.render(self.analytics)

        # history
        st.divider()
        self.history_view.render()

    def _render_form_section(self):
        """Render form section"""
        tabs = st.tabs(
            [
                "➕ Ćwiczenia",
                "🏋️‍♂️ Sesje treningowe",
                "📏 Pomiary ciała",
                "⚖️ Skład ciała",
            ]
        )

        with tabs[0]:
            ExerciseFormView().render()
        with tabs[1]:
            SessionFormView().render()
        with tabs[2]:
            BodyMeasurementsFormView().render()
        with tabs[3]:
            BodyCompositionFormView().render()

    def _render_exercise_analysis(self):
        # --- Selectbox ---
        exercises = self.dashboard_service.list_exercises()
        selected: Optional[str] = st.selectbox("Wybierz ćwiczenie", exercises)

        if not selected:
            st.warning("Brak danych dla wybranego ćwiczenia.")
            return

        session_summary, kpis, df_history = self.dashboard_service.get_exercise_analysis(selected)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- KPI ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.html(
                self.theme.create_kpi_card(
                    title="Szacowany 1RM", value=f"{kpis['latest_1rm']:.1f} kg"
                ).strip()
            )

        with col2:
            st.html(
                self.theme.create_kpi_card(
                    title="Progress od startu", value=f"{kpis['progress']:+.1f}%"
                ).strip()
            )

        with col3:
            st.html(
                self.theme.create_kpi_card(
                    title="Średni roboczy ciężar", value=f"{kpis['avg_weight']:.1f} kg"
                ).strip()
            )

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
        st.dataframe(df_history, hide_index=True, width="stretch")

    def _render_muscle_group_analysis(self):
        # Optional date filtering: only apply when user enables the filter
        filter_enabled = st.checkbox("Filtruj po dacie", value=False)
        date_from = None
        date_to = None
        if filter_enabled:
            col1, col2 = st.columns(2)
            # sensible defaults: dataset min/max if available
            min_date = None
            max_date = None
            try:
                if (
                    hasattr(self.analytics, "df_sets")
                    and not self.analytics.df_sets.empty
                ):
                    min_date = self.analytics.df_sets["SessionDate"].min().date()
                    max_date = self.analytics.df_sets["SessionDate"].max().date()
            except Exception:
                min_date = None
                max_date = None

            with col1:
                date_from = st.date_input("Data od", value=min_date)
            with col2:
                date_to = st.date_input("Data do", value=max_date)

        # Use the service layer to get muscle analytics (optionally filtered)
        muscles, kpis, summary = self.dashboard_service.get_muscle_data(
            date_from=date_from, date_to=date_to
        )

        kpi_cards = [
            {"title": "Najbardziej obciążona grupa", "value": kpis["most_loaded_bodypart"]},
            {"title": "Najmniej obciążona grupa", "value": kpis["least_loaded_bodypart"]},
            {"title": "Średnia liczba ćwiczeń / grupa", "value": f"{kpis['avg_exercises_per_bodypart']:.2f}"},
            {"title": "Średnia intensywność", "value": f"{kpis['avg_intensity']:.1f} %"},
        ]
        self.kpi_view.display(kpi_cards)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Charts use the MuscleAnalytics instance returned by the service
        self.charts_view.render_muscle_group_charts(muscles)

        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader("Podsumowanie")
        # render_muscle_summary_table expects a muscles-like object
        self.charts_view.render_muscle_summary_table(muscles)

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
        st.dataframe(df_history, hide_index=True, width="stretch")
