import streamlit as st
from datetime import date

class BodyCompositionForm:
    def input_composition(self):
        st.header("Dodaj analizę składu ciała")

        data = st.date_input("Data pomiaru", value=date.today())

        st.subheader("Podstawowe dane")
        waga = st.number_input("Waga (kg)", min_value=0.0)
        masa_miesniowa = st.number_input("Masa mięśniowa (kg)", min_value=0.0)
        masa_tluszczowa = st.number_input("Masa tłuszczowa (kg)", min_value=0.0)
        tkanka_tluszczowa = st.number_input("% tkanki tłuszczowej", min_value=0.0, max_value=100.0)
        procent_wody = st.number_input("% wody w organizmie", min_value=0.0, max_value=100.0)
        masa_wody = st.number_input("Masa wody (kg)", min_value=0.0)

        st.subheader("Masa mięśniowa w segmentach")
        miesnie_tulow = st.number_input("Tułów (kg)", min_value=0.0)
        miesnie_l_rece = st.number_input("Lewa ręka (kg)", min_value=0.0)
        miesnie_p_rece = st.number_input("Prawa ręka (kg)", min_value=0.0)
        miesnie_l_noga = st.number_input("Lewa noga (kg)", min_value=0.0)
        miesnie_p_noga = st.number_input("Prawa noga (kg)", min_value=0.0)

        st.subheader("Tłuszcz w segmentach")
        tluszcz_tulow = st.number_input("Tułów (%)", min_value=0.0, max_value=100.0)
        tluszcz_l_rece = st.number_input("Lewa ręka (%)", min_value=0.0, max_value=100.0)
        tluszcz_p_rece = st.number_input("Prawa ręka (%)", min_value=0.0, max_value=100.0)
        tluszcz_l_noga = st.number_input("Lewa noga (%)", min_value=0.0, max_value=100.0)
        tluszcz_p_noga = st.number_input("Prawa noga (%)", min_value=0.0, max_value=100.0)

        st.subheader("Dodatkowe")
        niechciany_tluszcz = st.number_input("Niechciany tłuszcz", min_value=0.0, max_value=100.0)
        notatka = st.text_input("Notatka")

        return (
            data, waga, masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa,
            procent_wody, masa_wody,
            miesnie_tulow, miesnie_l_rece, miesnie_p_rece, miesnie_l_noga, miesnie_p_noga,
            tluszcz_tulow, tluszcz_l_rece, tluszcz_p_rece, tluszcz_l_noga, tluszcz_p_noga,
            niechciany_tluszcz, notatka
        )
