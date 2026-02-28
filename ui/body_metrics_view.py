"""
Body Metrics View

Displays body composition and measurement trends with proportions and insights.

Styling strategy:
  - page_title / section_header / chart_label  → main.css handles rendering
  - st.metric                                  → main.css handles styling
  - st.tabs, st.form, st.expander              → main.css handles styling
  - line charts                                → line_chart() from ui_helpers (Vega-Lite themed)

Responsibilities:
  - Render pre-computed body metrics
  - Display trends, proportions, and insights from metrics layer
  - Provide form for adding new body composition/measurement data
  
All calculations are performed in metrics.body_metrics; this layer is presentation-only.
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from data_manager import DataManager
from ui.utils.ui_helpers import chart_label, line_chart, page_title, section_header


METRIC_CONFIG = {
    "composition": {
        "Weight": {"col": "weight", "unit": "kg", "best": "max"},
        "Muscle Mass": {"col": "muscle_mass", "unit": "kg", "best": "max"},
        "Fat Mass": {"col": "fat_mass", "unit": "kg", "best": "min"},
        "Water Mass": {"col": "water_mass", "unit": "kg", "best": "max"},
        "Body Fat": {"col": "fat_percentage", "unit": "%",  "best": "min"},
    },
    "measurements": {
        "Chest": {"col": "chest", "unit": "cm", "best": "max"},
        "Waist": {"col": "waist", "unit": "cm", "best": "min"},
        "Abdomen": {"col": "abdomen", "unit": "cm", "best": "min"},
        "Hips": {"col": "hips", "unit": "cm", "best": "min"},
        "Thigh": {"col": "thigh", "unit": "cm", "best": "max"},
        "Calf": {"col": "calf", "unit": "cm", "best": "max"},
        "Biceps": {"col": "biceps", "unit": "cm", "best": "max"},
    },
}


class BodyMetricsView:
    """UI view for body composition and measurement metrics.
    
    Displays pre-computed metrics from the body_metrics engine including:
    - Current body composition snapshot
    - Composition and measurement trends over time
    - Body proportions and recomposition quality 
    - Generated insights from trends
    - Forms for adding new measurements
    """

    def __init__(self, body_metrics: Dict) -> None:
        """Initialize view with pre-computed body metrics.
        
        Args:
            body_metrics: Dictionary containing:
                - timeline: List of timestamped measurements
                - global: Global summary metrics
                - proportions: Calculated body proportion ratios
                - recomposition: Recomposition quality metrics
                - insights: Generated trend insights
                - deltas: Change values for each metric
        """
        self.body_metrics = body_metrics
        self.dm = DataManager()

    def render(self) -> None:
        """Render the complete body metrics view."""
        page_title("Body Metrics", "Body Metrics")

        timeline = self.body_metrics.get("timeline", [])
        if not timeline:
            st.info("No body composition data available.")
            return

        df = pd.DataFrame(timeline)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        self._render_snapshot_kpis(df)
        self._render_composition_trends(df)
        self._render_recomposition_quality()
        self._render_measurement_trends(df)
        self._render_proportions()
        self._render_insights()
        self._add_measurement_form()

    def _render_snapshot_kpis(self, df: pd.DataFrame) -> None:
        """Render a snapshot of the latest key metrics."""
        section_header("Snapshot")

        latest = df.iloc[-1]
        deltas = self.body_metrics.get("deltas", {})
        
        cols = st.columns(4)

        delta_weight = deltas.get("weight")
        cols[0].metric("Weight", f"{latest['weight']} kg", f"{delta_weight} kg" if delta_weight is not None else "—")

        if "fat_percentage" in df.columns:
            delta_fat = deltas.get("fat_percentage")
            cols[1].metric("Body Fat %", f"{latest['fat_percentage']} %", f"{delta_fat} %" if delta_fat is not None else "—")

        if "muscle_mass" in df.columns:
            delta_muscle = deltas.get("muscle_mass")
            cols[2].metric("Muscle Mass", f"{latest['muscle_mass']} kg", f"{delta_muscle} kg" if delta_muscle is not None else "—")

        proportions = self.body_metrics.get("proportions", {})
        ratio_c2w = proportions.get("chest_to_waist")
        if ratio_c2w:
            delta_ratio = deltas.get("chest_to_waist")
            delta_text = f"{delta_ratio:+.2f}" if delta_ratio is not None else "—"
            cols[3].metric("Chest / Waist", f"{ratio_c2w}", delta=delta_text)

    def _render_composition_trends(self, df: pd.DataFrame) -> None:
        """Render body composition metric trends."""
        self._render_metric_trends_section(df, section_key="composition", title="Body Composition Trends")

    def _render_recomposition_quality(self) -> None:
        """Render recomposition quality metrics from metrics layer."""
        section_header("Weight Change Quality")
        st.caption("How much of your weight change comes from lean mass.")

        recomp = self.body_metrics.get("recomposition", {})
        lean_ratio = recomp.get("lean_mass_contribution_pct", 0)
        recomp_type = recomp.get("recomposition_type", "unknown")

        st.metric("Lean Mass Contribution", f"{lean_ratio} %")

        if recomp_type == "lean_bulk":
            st.success("Most weight change is lean mass — excellent recomposition.")
        elif recomp_type == "mixed_bulk":
            st.info("Mixed weight gain. Acceptable balance.")
        elif recomp_type == "fat_bulk":
            st.warning("Fat-dominant weight gain. Review nutrition.")
        elif recomp_type == "lean_cut":
            st.success("Lean mass loss minimized — good cut quality.")
        elif recomp_type == "mixed_cut":
            st.info("Mixed weight loss. Monitor muscle preservation.")
        elif recomp_type == "fat_loss":
            st.warning("Fat loss minimal — ensure caloric deficit is adequate.")
        elif recomp_type == "stable":
            st.info("Body weight stable — recomposition focus.")

    def _render_measurement_trends(self, df: pd.DataFrame) -> None:
        """Render body measurement trends."""
        self._render_metric_trends_section(df, section_key="measurements", title="Measurements")

    def _render_proportions(self) -> None:
        """Render body proportion ratios from pre-computed metrics."""
        section_header("Proportions")

        proportions = self.body_metrics.get("proportions", {})
        if not proportions:
            st.info("Not enough measurement data for proportions.")
            return

        cols = st.columns(3)

        c2w = proportions.get("chest_to_waist")
        if c2w:
            cols[0].metric("Chest / Waist", c2w, delta=" ")
            if c2w > 1.3:
                st.success("Strong upper-body dominance.")
            elif c2w < 1.1:
                st.warning("Consider upper-body hypertrophy focus.")

        # Thigh to waist ratio
        t2w = proportions.get("thigh_to_waist")
        if t2w:
            cols[1].metric("Thigh / Waist", t2w, delta=" ")

        # Biceps to waist ratio
        b2w = proportions.get("biceps_to_waist")
        if b2w:
            cols[2].metric("Biceps / Waist", b2w, delta=" ")

    def _render_insights(self) -> None:
        """Render pre-computed insights from metrics layer."""
        section_header("Insights")

        insights = self.body_metrics.get("insights", [])
        
        if insights:
            for insight in insights:
                st.success(insight)
        else:
            st.info("Not enough data for strong insights yet.")

    def _add_measurement_form(self) -> None:
        """Provide forms for adding new body composition and measurement data."""
        section_header("Add New Body Metrics")
        st.caption("Log body composition or measurements. One entry per day per type.")

        tabs = st.tabs(["Body Composition", "Body Measurements"])

        with tabs[0]:
            with st.form("body_composition_form"):
                date = st.date_input("Measurement date")
                weight = st.number_input("Weight (kg)", step=0.1)
                fat_pct = st.number_input("Body Fat (%)", step=0.1)
                muscle_mass = st.number_input("Muscle Mass (kg)", step=0.1)
                fat_mass = st.number_input("Fat Mass (kg)", step=0.1)
                water_mass = st.number_input("Water Mass (kg)", step=0.1)
                submitted = st.form_submit_button("Save Body Composition")

            if submitted:
                if self._measurement_exists(date, category="composition"):
                    st.error("Body composition for this date already exists.")
                else:
                    self._save_body_composition(
                        date, weight, fat_pct, muscle_mass, fat_mass, water_mass
                    )
                    st.success("Body composition saved.")
                    st.cache_data.clear()
                    st.rerun()

        with tabs[1]:
            with st.form("body_measurements_form"):
                date = st.date_input("Measurement date", key="measure_date")
                chest = st.number_input("Chest (cm)", step=0.1)
                waist = st.number_input("Waist (cm)", step=0.1)
                abdomen = st.number_input("Abdomen (cm)", step=0.1)
                hips = st.number_input("Hips (cm)", step=0.1)
                thigh = st.number_input("Thigh (cm)", step=0.1)
                calf = st.number_input("Calf (cm)", step=0.1)
                biceps = st.number_input("Biceps (cm)", step=0.1)
                submitted = st.form_submit_button("Save Measurements")

            if submitted:
                if self._measurement_exists(date, category="measurements"):
                    st.error("Body measurements for this date already exist.")
                else:
                    self._save_body_measurements(
                        date, chest, waist, abdomen, hips, thigh, calf, biceps
                    )
                    st.success("Body measurements saved.")
                    st.cache_data.clear()
                    st.rerun()

    def _render_metric_trends_section(self, df: pd.DataFrame, section_key: str, title: str) -> None:
        """Render a selectable metric trend with KPIs and chart."""
        section_header(title)
        st.caption("Track trends over time. KPI shows total change since first record.")

        section = METRIC_CONFIG.get(section_key, {})
        available = {
            label: cfg
            for label, cfg in section.items()
            if cfg["col"] in df.columns
        }

        if not available:
            st.info("No data available.")
            return

        selected_label = st.selectbox("Select metric", list(available.keys()), key=f"{section_key}_select")
        cfg = available[selected_label]
        col = cfg["col"]
        unit = cfg["unit"]
        best_mode = cfg["best"]

        self._render_metric_kpis(df, col, unit, best_mode)
        self._render_trend_insight(df, col, best_mode)

        chart_label(selected_label)
        trend_df = df.set_index("date")[[col]].rename(columns={col: selected_label})
        line_chart(trend_df, selected_label)

    def _render_metric_kpis(self, df: pd.DataFrame, col: str, unit: str, best_mode: str = "max") -> None:
        """Render current, average, and best values for a metric."""
        values = df[col].dropna()
        if values.empty:
            return

        current = round(values.iloc[-1], 2)
        avg = round(values.mean(), 2)
        best = round(values.min() if best_mode == "min" else values.max(), 2)
        delta = _calculate_delta(values)

        _, c1, c2, c3, _ = st.columns([1, 2, 2, 2, 1])
        c1.metric("Current", f"{current} {unit}", f"{delta} {unit}")
        c2.metric("Average", f"{avg} {unit}", f"{delta} {unit}")
        c3.metric("Best", f"{best} {unit}", f"{delta} {unit}")

    def _render_trend_insight(self, df: pd.DataFrame, col: str, best_mode: str) -> None:
        """Render directional insight based on metric trend."""
        values = df[col].dropna()
        if len(values) < 2:
            return

        delta = values.iloc[-1] - values.iloc[0]
        
        if best_mode == "min":
            if delta < 0:
                st.success("Trend improving over time.")
            elif delta > 0:
                st.warning("Trend worsening over time.")
        else:
            if delta > 0:
                st.success("Positive upward trend.")
            elif delta < 0:
                st.warning("Negative downward trend.")

    def _measurement_exists(self, date, category: str) -> bool:
        """Check if a measurement exists for the given date."""
        timeline = self.body_metrics.get("timeline", [])
        if not timeline:
            return False

        def _has_value(val) -> bool:
            if val is None:
                return False
            try:
                from math import isnan
                return not (isinstance(val, float) and isnan(val))
            except ImportError:
                return True

        for r in timeline:
            if r["date"] == date:
                if category == "composition" and _has_value(r.get("weight")):
                    return True
                if category == "measurements":
                    for k in ["chest", "waist", "abdomen", "hips", "thigh", "calf", "biceps"]:
                        if _has_value(r.get(k)):
                            return True
        return False

    def _save_body_composition(self, date, weight, fat_pct, muscle_mass, fat_mass, water_mass) -> None:
        """Save body composition data to database."""
        self.dm.add_body_composition({
            "date": date,
            "weight": weight,
            "muscle_mass": muscle_mass,
            "fat_mass": fat_mass,
            "water_mass": water_mass,
            "bf_percent": fat_pct,
            "method": "SmartWatch",
        })

    def _save_body_measurements(self, date, chest, waist, abdomen, hips, thigh, calf, biceps) -> None:
        """Save body measurements data to database."""
        self.dm.add_body_measurements({
            "date": date,
            "chest": chest,
            "waist": waist,
            "abdomen": abdomen,
            "hips": hips,
            "thigh": thigh,
            "calf": calf,
            "biceps": biceps,
        })

def _calculate_delta(values: pd.Series) -> float | None:
    """Calculate change from first to last value.
    
    Args:
        values: Series of numeric values
    
    Returns:
        Change value rounded to 2 decimals, or None if insufficient data
    """
    if values.empty or len(values) < 2:
        return None
    return round(values.iloc[-1] - values.iloc[0], 2)
