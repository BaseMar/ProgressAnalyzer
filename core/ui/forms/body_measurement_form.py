import streamlit as st
from datetime import date
from core.data_manager import DataManager
from .base_form import BaseFormView

class BodyMeasurementsFormView(BaseFormView):
    """Formularz dodawania pomiarów ciała."""

    def __init__(self):
        super().__init__("Dodaj pomiary ciała")
        self.data_manager = DataManager()

    def render_form(self):
        with st.form("body_measurements_form"):
            measurement_date = st.date_input("Data pomiaru", date.today())

            col1, col2, col3 = st.columns(3)
            with col1:
                chest = st.number_input("Klatka piersiowa (cm)", min_value=0.0, step=0.1)
                waist = st.number_input("Talia (cm)", min_value=0.0, step=0.1)
                abdomen = st.number_input("Brzuch (cm)", min_value=0.0, step=0.1)
            with col2:
                hips = st.number_input("Biodra (cm)", min_value=0.0, step=0.1)
                thigh = st.number_input("Udo (cm)", min_value=0.0, step=0.1)
                calf = st.number_input("Łydka (cm)", min_value=0.0, step=0.1)
            with col3:
                biceps = st.number_input("Biceps (cm)", min_value=0.0, step=0.1)

            submitted = st.form_submit_button("Zapisz pomiar")

            if submitted:
                data = {
                    "date": measurement_date,
                    "chest": chest,
                    "waist": waist,
                    "abdomen": abdomen,
                    "hips": hips,
                    "thigh": thigh,
                    "calf": calf,
                    "biceps": biceps,
                }

                success = self.data_manager.add_body_measurements(data)
                
                if success:
                    st.success(f"✅ Pomiary z dnia {measurement_date} zostały dodane!")
                else:
                    st.error("❌ Błąd podczas zapisu pomiarów.")
