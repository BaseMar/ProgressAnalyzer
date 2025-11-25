import streamlit as st
from core.services.body_metrics_service import BodyMetricsService
from core.ui.kpi_view import KPIView
from core.ui.charts_view import ChartsView

class BodyMetricsView:

    def __init__(self, theme):
        self.service = BodyMetricsService()
        self.kpi_view = KPIView(theme)
        self.charts_view = ChartsView(theme)

    def render(self):
        # ---- get filtered data + computed KPIs
        data = self.service.get_body_data()
        measurements = data["measurements"]
        composition = data["composition"]
        kpis = data["kpis"]

        # ---- render KPIs
        self.kpi_view.display(kpis)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ---- Render charts selection
        self._render_charts(measurements, composition)

    def _render_charts(self, measurements, composition):
        col_m, col_c = st.columns(2)

        with col_m:
            metric = st.selectbox(
                "Measurement Metric",
                ["Chest", "Waist", "Abdomen", "Hips", "Thigh", "Calf", "Biceps"],
                index=0
            )

        with col_c:
            comp_metric = st.selectbox(
                "Composition Metric",
                ["Weight", "Muscle Mass", "Fat Mass", "Body Fat %", "Water Mass"],
                index=0
            )

        col_left, col_right = st.columns(2)

        with col_left:
            self.charts_view.render_metric_trend(measurements, None, metric)

        with col_right:
            self.charts_view.render_metric_trend(None, composition, comp_metric)
