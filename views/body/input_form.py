import datetime
import streamlit as st

class BodyMeasurementsForm:
    def input_body_measurements(self):
        st.header("Dodaj pomiary ciała")
        data = st.date_input("Data pomiaru:", datetime.date.today())

        basics = [
            "Klatka piersiowa (cm)", "Talia (cm)", "Brzuch (cm)",
            "Biodra (cm)", "Udo (cm)", "Łydka (cm)", "Ramię/Biceps (cm)"
        ]
        values = [st.number_input(k, min_value=0.0, step=0.1) for k in basics]

        notatka = st.text_input("Notatka (opcjonalnie)")

        return (data, *values, notatka)