from datetime import date

from typing import Any, Dict

import streamlit as st

from core.data_manager import DataManager

from .base_form import BaseFormView


class BodyMeasurementsFormView(BaseFormView):
    """Form view for recording body measurements (chest, waist, hips, etc.)."""

    def __init__(self) -> None:
        """Initialize the body measurements form view."""
        super().__init__("Add Body Measurements")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the body measurements form with input fields for all body parts."""
        with st.form("body_measurements_form"):
            measurement_date: date = st.date_input("Measurement Date", date.today())

            col1, col2, col3 = st.columns(3)
            with col1:
                chest: float = st.number_input(
                    "Chest (cm)", min_value=0.0, step=0.1
                )
                waist: float = st.number_input("Waist (cm)", min_value=0.0, step=0.1)
                abdomen: float = st.number_input("Abdomen (cm)", min_value=0.0, step=0.1)
            with col2:
                hips: float = st.number_input("Hips (cm)", min_value=0.0, step=0.1)
                thigh: float = st.number_input("Thigh (cm)", min_value=0.0, step=0.1)
                calf: float = st.number_input("Calf (cm)", min_value=0.0, step=0.1)
            with col3:
                biceps: float = st.number_input("Biceps (cm)", min_value=0.0, step=0.1)

            submitted: bool = st.form_submit_button("Save Measurement")

            if submitted:
                data: Dict[str, Any] = {
                    "date": measurement_date,
                    "chest": chest,
                    "waist": waist,
                    "abdomen": abdomen,
                    "hips": hips,
                    "thigh": thigh,
                    "calf": calf,
                    "biceps": biceps,
                }

                success: bool = self.data_manager.add_body_measurements(data)

                if success:
                    st.success(f"✅ Measurements from {measurement_date} have been added!")
                else:
                    st.error("❌ Error while saving measurements.")
