import datetime
import streamlit as st

class BodyMeasurementsForm:
    def input_body_measurements(self):
        st.header("Dodaj pomiary ciała")
        data = st.date_input("Data pomiaru:", datetime.date.today())

        basics = [
            "Waga (kg)", "Klatka piersiowa (cm)", "Talia (cm)", "Brzuch (cm)",
            "Biodra (cm)", "Udo (cm)", "Łydka (cm)", "Ramię/Biceps (cm)"
        ]
        values = [st.number_input(k, min_value=0.0, step=0.1) for k in basics]

        st.subheader("Skład ciała (opcjonalnie)")
        masa_miesniowa = st.number_input("Masa mięśniowa (kg)", min_value=0.0, step=0.1)
        masa_tluszczowa = st.number_input("Masa tłuszczowa (kg)", min_value=0.0, step=0.1)
        tkanka_tluszczowa = st.number_input("Tkanka tłuszczowa (%)", min_value=0.0, step=0.1)
        woda = st.number_input("Woda w ciele (kg)", min_value=0.0, step=0.1)
        notatka = st.text_input("Notatka (opcjonalnie)")

        return (data, *values, masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa, woda, notatka)