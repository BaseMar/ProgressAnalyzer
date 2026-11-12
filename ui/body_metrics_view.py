"""Body composition and measurement trends view."""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from data_manager import DataManager
from ui.utils.ui_helpers import line_chart, section_header

METRIC_CONFIG = {
    "composition": {
        "Weight": {"col": "weight", "unit": "kg"},
        "Muscle Mass": {"col": "muscle_mass", "unit": "kg"},
        "Fat Mass": {"col": "fat_mass", "unit": "kg"},
        "Water Mass": {"col": "water_mass", "unit": "kg"},
        "Body Fat": {"col": "fat_percentage", "unit": "%"},
    },
    "measurements": {
        "Chest": {"col": "chest", "unit": "cm"},
        "Waist": {"col": "waist", "unit": "cm"},
        "Abdomen": {"col": "abdomen", "unit": "cm"},
        "Hips": {"col": "hips", "unit": "cm"},
        "Thigh": {"col": "thigh", "unit": "cm"},
        "Calf": {"col": "calf", "unit": "cm"},
        "Biceps": {"col": "biceps", "unit": "cm"},
    },
}


class BodyMetricsView:
    """Recorded measurement analysis and forms for adding body records."""

    def __init__(self, body_metrics: Dict, *, manager=None) -> None:
        """Use a recorded timeline and the UI-facing persistence manager."""
        self.body_metrics = body_metrics
        self.dm = manager if manager is not None else DataManager()

    def render(self) -> None:
        """Render the selected recorded measurement and its source dates."""
        timeline = self.body_metrics.get("timeline", [])
        if not timeline:
            st.info("No body composition data available.")
            return

        df = pd.DataFrame(timeline)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        available = {
            label: cfg
            for group in METRIC_CONFIG.values()
            for label, cfg in group.items()
            if cfg["col"] in df and df[cfg["col"]].notna().any()
        }
        if not available:
            st.info("No measurements in this period. Add a measurement in History.")
            return
        if st.session_state.get("analysis_body_metric") not in available:
            st.session_state["analysis_body_metric"] = next(iter(available))
        selected = st.selectbox("Measurement", list(available), key="analysis_body_metric")
        cfg = available[selected]
        points = df[["date", cfg["col"]]].dropna().rename(columns={cfg["col"]: selected})
        current = points.iloc[-1]
        delta = current[selected] - points.iloc[0][selected]
        change_unit = "pp" if cfg["unit"] == "%" else cfg["unit"]
        latest, change, recorded = st.columns(3)
        latest.metric(f"Latest {selected.lower()}", f"{current[selected]:g} {cfg['unit']}")
        change.metric(
            "Change in selected period",
            f"{delta:+g} {change_unit}" if len(points) > 1 else "—",
            help=f"Compared with the first available measurement on {points.iloc[0]['date']:%d %b %Y}. Direction alone does not establish improvement.",
        )
        recorded.metric("Last measured", f"{current['date']:%d %b %Y}")
        if len(points) == 1:
            st.caption("One observation; no trend yet.")
        line_chart(points.set_index("date"), selected)
        st.caption(
            "These are recorded measurements. Direction alone does not establish improvement; device estimates may vary."
        )

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
                    st.rerun()

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

    def _save_body_composition(
        self, date, weight, fat_pct, muscle_mass, fat_mass, water_mass
    ) -> None:
        """Save body composition data to database."""
        self.dm.add_body_composition(
            {
                "date": date,
                "weight": weight,
                "muscle_mass": muscle_mass,
                "fat_mass": fat_mass,
                "water_mass": water_mass,
                "bf_percent": fat_pct,
                "method": "SmartWatch",
            }
        )

    def _save_body_measurements(
        self, date, chest, waist, abdomen, hips, thigh, calf, biceps
    ) -> None:
        """Save body measurements data to database."""
        self.dm.add_body_measurements(
            {
                "date": date,
                "chest": chest,
                "waist": waist,
                "abdomen": abdomen,
                "hips": hips,
                "thigh": thigh,
                "calf": calf,
                "biceps": biceps,
            }
        )
