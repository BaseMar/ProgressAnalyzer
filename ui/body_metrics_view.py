"""
Body Metrics view for the UI layer.

Styling strategy (mirrors dashboard_view.py):
  - page_title / section_header / chart_label  → main.css handles rendering
  - st.metric                                  → main.css handles styling
  - st.tabs, st.form, st.expander              → main.css handles styling
  - line charts                                → line_chart() from ui_helpers (Vega-Lite themed)
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from data_manager import DataManager
from ui.utils.ui_helpers import chart_label, fmt_num, line_chart, page_title, section_header

METRIC_CONFIG = {
    "composition": {
        "Weight":      {"col": "weight",         "unit": "kg", "best": "max"},
        "Muscle Mass": {"col": "muscle_mass",     "unit": "kg", "best": "max"},
        "Fat Mass":    {"col": "fat_mass",        "unit": "kg", "best": "min"},
        "Water Mass":  {"col": "water_mass",      "unit": "kg", "best": "max"},
        "Body Fat":    {"col": "fat_percentage",  "unit": "%",  "best": "min"},
    },
    "measurements": {
        "Chest":   {"col": "chest",   "unit": "cm", "best": "max"},
        "Waist":   {"col": "waist",   "unit": "cm", "best": "min"},
        "Abdomen": {"col": "abdomen", "unit": "cm", "best": "min"},
        "Hips":    {"col": "hips",    "unit": "cm", "best": "min"},
        "Thigh":   {"col": "thigh",   "unit": "cm", "best": "max"},
        "Calf":    {"col": "calf",    "unit": "cm", "best": "max"},
        "Biceps":  {"col": "biceps",  "unit": "cm", "best": "max"},
    },
}


class BodyMetricsView:
    def __init__(self, body_metrics: Dict) -> None:
        self.body_metrics = body_metrics
        self.dm = DataManager()

    def render(self) -> None:
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
        self._weight_quality(df)
        self._render_measurement_trends(df)
        self._proportions_section(df)
        self._insights(df)
        self._add_measurement_form()

    def _render_snapshot_kpis(self, df: pd.DataFrame) -> None:
        section_header("Snapshot")

        latest = df.iloc[-1]
        cols = st.columns(4)

        cols[0].metric("Weight", f"{latest['weight']} kg", f"{self._calculate_delta(df, 'weight')} kg")

        if "fat_percentage" in df.columns:
            cols[1].metric("Body Fat %", f"{latest['fat_percentage']} %", f"{self._calculate_delta(df, 'fat_percentage')} %")

        if "muscle_mass" in df.columns:
            cols[2].metric("Muscle Mass", f"{latest['muscle_mass']} kg", f"{self._calculate_delta(df, 'muscle_mass')} kg")

        if "waist" in df.columns and "chest" in df.columns:
            ratio = round(latest["chest"] / latest["waist"], 2)
            cols[3].metric("Chest / Waist", ratio, delta="")

    def _render_composition_trends(self, df: pd.DataFrame) -> None:
        self._render_metric_trends_section(df, section_key="composition", title="Body Composition Trends")

    def _weight_quality(self, df: pd.DataFrame) -> None:
        section_header("Weight Change Quality")
        st.caption("How much of your weight change comes from lean mass.")

        if not {"weight", "muscle_mass", "fat_percentage"}.issubset(df.columns):
            st.info("Not enough data for recomposition analysis.")
            return

        delta_weight = df["weight"].iloc[-1] - df["weight"].iloc[0]
        delta_muscle = df["muscle_mass"].iloc[-1] - df["muscle_mass"].iloc[0]
        lean_ratio   = round((delta_muscle / delta_weight * 100) if delta_weight else 0, 1)

        st.metric("Lean Mass Contribution", f"{lean_ratio} %")

        if lean_ratio > 60:
            st.success("Most weight change is lean mass — excellent recomposition.")
        elif lean_ratio > 30:
            st.info("Mixed weight gain. Acceptable balance.")
        else:
            st.warning("Fat-dominant weight gain. Review nutrition.")

        if abs(delta_weight) < 0.5:
            st.info("Body weight stable — recomposition focus.")

    def _render_measurement_trends(self, df: pd.DataFrame) -> None:
        self._render_metric_trends_section(df, section_key="measurements", title="Measurements")

    def _proportions_section(self, df: pd.DataFrame) -> None:
        section_header("Proportions")

        latest = df.iloc[-1]
        cols   = st.columns(3)

        if "waist" in df.columns and "chest" in df.columns:
            ratio = round(latest["chest"] / latest["waist"], 2)
            cols[0].metric("Chest / Waist", ratio, delta=" ")
            if ratio > 1.3:
                st.success("Strong upper-body dominance.")
            elif ratio < 1.1:
                st.warning("Consider upper-body hypertrophy focus.")

        if "waist" in df.columns and "thigh" in df.columns:
            cols[1].metric("Thigh / Waist", round(latest["thigh"] / latest["waist"], 2), delta=" ")

        if "waist" in df.columns and "biceps" in df.columns:
            cols[2].metric("Biceps / Waist", round(latest["biceps"] / latest["waist"], 2), delta=" ")

    def _insights(self, df: pd.DataFrame) -> None:
        section_header("Insights")

        insights = []

        if "weight" in df.columns and df["weight"].iloc[-1] > df["weight"].iloc[0]:
            insights.append("Weight trending up.")

        if "fat_percentage" in df.columns:
            if df["fat_percentage"].iloc[-1] < df["fat_percentage"].iloc[0]:
                insights.append("Body fat decreasing — good recomposition.")

        if "waist" in df.columns and "thigh" in df.columns:
            if df["waist"].iloc[-1] > df["thigh"].iloc[-1]:
                insights.append("Waist growth outpacing legs — consider volume redistribution.")

        if insights:
            for insight in insights:
                st.success(insight)
        else:
            st.info("Not enough data for strong insights yet.")

    def _add_measurement_form(self) -> None:
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
                    self._save_body_composition(date, weight, fat_pct, muscle_mass, fat_mass, water_mass)
                    st.success("Body composition saved.")
                    st.cache_data.clear()
                    st.rerun()

        with tabs[1]:
            with st.form("body_measurements_form"):
                date = st.date_input("Measurement date", key="measure_date")
                chest = st.number_input("Chest (cm)",   step=0.1)
                waist = st.number_input("Waist (cm)",   step=0.1)
                abdomen = st.number_input("Abdomen (cm)", step=0.1)
                hips = st.number_input("Hips (cm)",    step=0.1)
                thigh = st.number_input("Thigh (cm)",   step=0.1)
                calf = st.number_input("Calf (cm)",    step=0.1)
                biceps = st.number_input("Biceps (cm)",  step=0.1)
                submitted = st.form_submit_button("Save Measurements")

            if submitted:
                if self._measurement_exists(date, category="measurements"):
                    st.error("Body measurements for this date already exist.")
                else:
                    self._save_body_measurements(date, chest, waist, abdomen, hips, thigh, calf, biceps)
                    st.success("Body measurements saved.")
                    st.cache_data.clear()
                    st.rerun()

    def _render_metric_trends_section(self, df: pd.DataFrame, section_key: str, title: str) -> None:
        section_header(title)
        st.caption("Track trends over time. KPI shows total change since first record.")

        section   = METRIC_CONFIG.get(section_key, {})
        available = {label: cfg for label, cfg in section.items() if cfg["col"] in df.columns}

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

        # Themed Vega-Lite line chart via ui_helpers — matches all other views
        chart_label(selected_label)
        trend_df = df.set_index("date")[[col]].rename(columns={col: selected_label})
        line_chart(trend_df, selected_label)

    def _render_metric_kpis(self, df: pd.DataFrame, col: str, unit: str, best_mode: str = "max") -> None:
        values = df[col].dropna()
        if values.empty:
            return

        current = round(values.iloc[-1], 2)
        avg = round(values.mean(), 2)
        best = round(values.min() if best_mode == "min" else values.max(), 2)
        delta = self._calculate_delta(df, col)

        _, c1, c2, c3, _ = st.columns([1, 2, 2, 2, 1])
        c1.metric("Current", f"{current} {unit}", f"{delta} {unit}")
        c2.metric("Average", f"{avg} {unit}", f"{delta} {unit}")
        c3.metric("Best", f"{best} {unit}", f"{delta} {unit}")

    def _render_trend_insight(self, df: pd.DataFrame, col: str, best_mode: str) -> None:
        delta = self._calculate_delta(df, col)
        if delta is None:
            return
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

    def _calculate_delta(self, df: pd.DataFrame, col: str) -> float | None:
        if col not in df.columns or df[col].dropna().empty:
            return None
        values = df[col].dropna()
        return round(values.iloc[-1] - values.iloc[0], 2)

    def _measurement_exists(self, date, category: str) -> bool:
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
        self.dm.add_body_composition({
            "date": date, "weight": weight, "muscle_mass": muscle_mass,
            "fat_mass": fat_mass, "water_mass": water_mass,
            "bf_percent": fat_pct, "method": "SmartWatch",
        })

    def _save_body_measurements(self, date, chest, waist, abdomen, hips, thigh, calf, biceps) -> None:
        self.dm.add_body_measurements({
            "date": date, "chest": chest, "waist": waist, "abdomen": abdomen,
            "hips": hips, "thigh": thigh, "calf": calf, "biceps": biceps,
        })
