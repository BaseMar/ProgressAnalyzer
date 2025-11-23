from datetime import date

from typing import Any, Dict

import streamlit as st

from core.data_manager import DataManager

from .base_form import BaseFormView


class BodyMeasurementsFormView(BaseFormView):
    """Form view for recording body measurements (chest, waist, hips, etc.)."""

    def __init__(self) -> None:
        """Initialize the body measurements form view."""
        super().__init__("Dodaj pomiary ciała")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the body measurements form with input fields for all body parts."""
        with st.form("body_measurements_form"):
            measurement_date: date = st.date_input("Data pomiaru", date.today())

            col1, col2, col3 = st.columns(3)
            with col1:
                chest: float = st.number_input(
                    "Klatka piersiowa (cm)", min_value=0.0, step=0.1
                )
                waist: float = st.number_input("Talia (cm)", min_value=0.0, step=0.1)
                abdomen: float = st.number_input("Brzuch (cm)", min_value=0.0, step=0.1)
            with col2:
                hips: float = st.number_input("Biodra (cm)", min_value=0.0, step=0.1)
                thigh: float = st.number_input("Udo (cm)", min_value=0.0, step=0.1)
                calf: float = st.number_input("Łydka (cm)", min_value=0.0, step=0.1)
            with col3:
                biceps: float = st.number_input("Biceps (cm)", min_value=0.0, step=0.1)

            submitted: bool = st.form_submit_button("Zapisz pomiar")

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
                    st.success(f"✅ Pomiary z dnia {measurement_date} zostały dodane!")
                else:
                    st.error("❌ Błąd podczas zapisu pomiarów.")
