from datetime import date

from typing import Any, Dict

import streamlit as st

from core.data_manager import DataManager

from .base_form import BaseFormView


class BodyCompositionFormView(BaseFormView):
    """Form view for recording body composition (weight, muscle mass, fat %, etc.)."""

    def __init__(self) -> None:
        """Initialize the body composition form view."""
        super().__init__("Add Body Composition")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the body composition form with input fields for weight, muscle/fat mass and percentages."""
        with st.form("body_composition_form"):
            measurement_date: date = st.date_input("Measurement Date", date.today())

            col1, col2, col3 = st.columns(3)
            with col1:
                weight: float = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
                muscle_mass: float = st.number_input(
                    "Muscle Mass (kg)", min_value=0.0, step=0.1
                )
            with col2:
                fat_mass: float = st.number_input(
                    "Fat Mass (kg)", min_value=0.0, step=0.1
                )
                water_mass: float = st.number_input("Water Mass (kg)", min_value=0.0, step=0.1)
            with col3:
                bf_percent: float = st.number_input(
                    "Body Fat %", min_value=0.0, max_value=100.0, step=0.1
                )
                method: str = st.selectbox(
                    "Measurement Method", ["SmartWatch", "Body Scale", "Other"]
                )

            submitted: bool = st.form_submit_button("Save Body Composition")

            if submitted:
                data: Dict[str, Any] = {
                    "date": measurement_date,
                    "weight": weight,
                    "muscle_mass": muscle_mass,
                    "fat_mass": fat_mass,
                    "water_mass": water_mass,
                    "bf_percent": bf_percent,
                    "method": method,
                }

                ok: bool = self.data_manager.add_body_composition(data)
                if ok:
                    st.success(
                        f"✅ Body composition from {measurement_date} has been saved!"
                    )
                else:
                    st.error("❌ Error while saving body composition.")
