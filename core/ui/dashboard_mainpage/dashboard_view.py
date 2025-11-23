import streamlit as st
from typing import Any, Optional
import pandas as pd

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
        elif selected_section == "Forms":
            self._render_form_section()
        elif selected_section == "Exercise Analysis":
            self._render_exercise_analysis()
        elif selected_section == "Muscle Groups":
            self._render_muscle_group_analysis()
        elif selected_section == "Body Measurements":
            self._render_body_measurements()

        # Footer
        self.footer_view.render()

    def _render_main_dashboard(self):
        """Render main dashboard content"""
        # KPI Cards
        kpis = self.dashboard_service.get_dashboard_kpis()
        kpi_cards = [
            {
                "title": "Average Intensity",
                "value": f"{kpis['avg_intensity']:.1f} %",
                "delta": f"Δ {kpis['intensity_change']}%",
            },
            {
                "title": "Total Weekly Volume",
                "value": f"{kpis['total_volume']:,.0f}".replace(",", " ") + " kg",
                "delta": f"Δ {kpis['volume_change']}%",
            },
            {"title": "Number of Sessions", "value": str(kpis["sessions"]), "delta": None},
            {
                "title": "Avg Sets per Session",
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
                "➕ Exercises",
                "🏋️‍♂️ Workout Sessions",
                "📏 Body Measurements",
                "⚖️ Body Composition",
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
        selected: Optional[str] = st.selectbox("Select Exercise", exercises)

        if not selected:
            st.warning("No data for the selected exercise.")
            return

        session_summary, kpis, df_history = self.dashboard_service.get_exercise_analysis(selected)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- KPI ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.html(
                self.theme.create_kpi_card(
                    title="Estimated 1RM", value=f"{kpis['latest_1rm']:.1f} kg"
                ).strip()
            )

        with col2:
            st.html(
                self.theme.create_kpi_card(
                    title="Progress from Start", value=f"{kpis['progress']:+.1f}%"
                ).strip()
            )

        with col3:
            st.html(
                self.theme.create_kpi_card(
                    title="Average Working Weight", value=f"{kpis['avg_weight']:.1f} kg"
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
        st.subheader(f"Exercise History: {selected}")
        st.dataframe(df_history, hide_index=True, width="stretch")

    def _render_muscle_group_analysis(self):
        # Optional date filtering: only apply when user enables the filter
        filter_enabled = st.checkbox("Filter by Date", value=False)
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
                date_from = st.date_input("From Date", value=min_date)
            with col2:
                date_to = st.date_input("To Date", value=max_date)

        # Use the service layer to get muscle analytics (optionally filtered)
        muscles, kpis, summary = self.dashboard_service.get_muscle_data(
            date_from=date_from, date_to=date_to
        )

        kpi_cards = [
            {"title": "Most Loaded Group", "value": kpis["most_loaded_bodypart"]},
            {"title": "Least Loaded Group", "value": kpis["least_loaded_bodypart"]},
            {"title": "Avg Exercises per Group", "value": f"{kpis['avg_exercises_per_bodypart']:.2f}"},
            {"title": "Average Intensity", "value": f"{kpis['avg_intensity']:.1f} %"},
        ]
        self.kpi_view.display(kpi_cards)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Charts use the MuscleAnalytics instance returned by the service
        self.charts_view.render_muscle_group_charts(muscles)

        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader("Summary")
        # render_muscle_summary_table expects a muscles-like object
        self.charts_view.render_muscle_summary_table(muscles)

    def _render_body_measurements(self):
        """Render body measurements section: filters, KPIs and charts."""
        st.header("📏 Body Metrics")

        # Load body data via DataManager
        from core.data_manager import DataManager

        data_mgr = DataManager()
        body_data = data_mgr.load_body_data()
        measurements = body_data.get("measurements")
        composition = body_data.get("composition")

        # --- Source filter for composition method ---
        method_options = ["All"]
        if composition is not None and not composition.empty:
            methods = composition["Method"].dropna().unique().tolist()
            method_options += sorted([m for m in methods if m not in method_options])
        method = st.selectbox("Data Source", method_options, index=0)

        # Prepare filtered dataframes (no date range filtering — use full history)
        def _filter_df(df):
            if df is None or df.empty:
                return None
            df2 = df.copy()
            df2["MeasurementDate"] = pd.to_datetime(df2["MeasurementDate"]) if "MeasurementDate" in df2.columns else pd.to_datetime(df2["SessionDate"]) if "SessionDate" in df2.columns else None
            if "Method" in df2.columns and method and method != "All":
                df2 = df2[df2["Method"] == method]
            return df2

        measurements_f = _filter_df(measurements)
        composition_f = _filter_df(composition)

        # --- KPIs ---
        kpi_cards = []
        if composition_f is None or composition_f.empty:
            st.info("No body composition data available for selected filters.")
            # still render empty KPI placeholders
            kpi_cards = [
                {"title": "Weight", "value": "—", "delta": None},
                {"title": "Muscle Mass", "value": "—", "delta": None},
                {"title": "Body Fat %", "value": "—", "delta": None},
            ]
        else:
            comp = composition_f.sort_values(by=["MeasurementDate"]).reset_index(drop=True)
            latest = comp.iloc[-1]
            prev = comp.iloc[-2] if comp.shape[0] > 1 else None

            def _delta(curr, prev):
                try:
                    if prev is None:
                        return None
                    d = float(curr) - float(prev)
                    sign = f"{d:+.1f}"
                    return sign
                except Exception:
                    return None

            w_val = f"{latest.get('Weight', '—'):.1f} kg" if pd.notna(latest.get("Weight", None)) else "—"
            m_val = f"{latest.get('MuscleMass', '—'):.1f} kg" if pd.notna(latest.get("MuscleMass", None)) else "—"
            bf_val = f"{latest.get('BodyFatPercentage', '—'):.1f}%" if pd.notna(latest.get("BodyFatPercentage", None)) else "—"

            kpi_cards = [
                {"title": "Weight", "value": w_val, "delta": _delta(latest.get('Weight', None), prev.get('Weight', None) if prev is not None else None)},
                {"title": "Muscle Mass", "value": m_val, "delta": _delta(latest.get('MuscleMass', None), prev.get('MuscleMass', None) if prev is not None else None)},
                {"title": "Body Fat %", "value": bf_val, "delta": _delta(latest.get('BodyFatPercentage', None), prev.get('BodyFatPercentage', None) if prev is not None else None)},
            ]

        self.kpi_view.display(kpi_cards)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- Metric selectors (separate for measurements and composition) ---
        col_m, col_c = st.columns(2)
        with col_m:
            measurement_options = ["Chest", "Waist", "Abdomen", "Hips", "Thigh", "Calf", "Biceps"]
            selected_measurement = st.selectbox("Measurement Metric", measurement_options, index=0)

        with col_c:
            composition_options = ["Weight", "Muscle Mass", "Fat Mass", "Body Fat %", "Water Mass"]
            selected_composition = st.selectbox("Composition Metric", composition_options, index=0)

        # --- Charts: two time-series side-by-side ---
        col_left, col_right = st.columns(2)
        with col_left:
            self.charts_view.render_metric_trend(measurements_f, None, selected_measurement)
        with col_right:
            self.charts_view.render_metric_trend(None, composition_f, selected_composition)

        st.markdown("<hr>", unsafe_allow_html=True)

        # --- Radar chart (latest circumferences) ---
        self.charts_view.render_circumference_radar(measurements_f)

    def _render_exercise_kpis(self, session_summary):
        latest_1rm = session_summary["Est1RM"].iloc[-1]
        start_1rm = session_summary["Est1RM"].iloc[0]
        progress = ((latest_1rm - start_1rm) / start_1rm * 100) if start_1rm > 0 else 0
        avg_weight = session_summary["Weight"].mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("Estimated 1RM", f"{latest_1rm:.1f} kg")
        col2.metric("Progress", f"{progress:+.1f}%")
        col3.metric("Average Working Weight", f"{avg_weight:.1f} kg")

    def _render_exercise_history(self, df_history, exercise_name):
        st.subheader(f"Exercise History: {exercise_name}")
        st.dataframe(df_history, hide_index=True, width="stretch")
