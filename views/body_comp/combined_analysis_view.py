import streamlit as st
import pandas as pd
from analytics.combine_analysis import merge_body_data_with_tolerance
from analytics.combine_analysis import generate_combined_analysis
from analytics.combine_analysis import compare_to_ideal
from analytics.combine_analysis import analyze_combined_ratios_over_time

class CombinedBodyAnalysisView:
    def __init__(self, body_measurements, body_composition):
        self.measurements = body_measurements
        self.composition = body_composition
        self.combined_data = merge_body_data_with_tolerance(body_measurements, body_composition)

    def display(self):
        st.title("Połączona analiza: Skład ciała + Obwody")

        if not self.combined_data:
            st.warning("Brak danych do połączenia.")
            return

        data = self.combined_data[0]
        st.subheader(f"Data: {data['DataPomiaru'].strftime('%d.%m.%Y')}")

        with st.expander("Obwody ciała"):
            st.dataframe(pd.DataFrame([{
                "Klatka piersiowa": data["KlatkaPiersiowa"],
                "Talia": data["Talia"],
                "Biodra": data["Biodra"],
                "Udo": data["Udo"],
                "Łydka": data["Lydka"],
                "Ramię": data["Ramie"],
            }]), use_container_width=True)

        with st.expander("Mięśnie (kg)"):
            st.dataframe(pd.DataFrame([{
                "Masa mięśniowa": data["MasaMiesniowa"],
                "Tulow": data["MiesnieTulow"],
                "L. Ręka": data["MiesnieLRece"],
                "P. Ręka": data["MiesniePRece"],
                "L. Noga": data["MiesnieLNoga"],
                "P. Noga": data["MiesniePNoga"],
            }]), use_container_width=True)

        with st.expander("Tłuszcz (kg / %)"):
            st.dataframe(pd.DataFrame([{
                "Masa tłuszczowa": data["MasaTluszczowa"],
                "Tkanka tłuszczowa [%]": data["TkankaTluszczowa"],
                "Tulow": data["TluszczTulow"],
                "L. Ręka": data["TluszczLRece"],
                "P. Ręka": data["TluszczPRece"],
                "L. Noga": data["TluszczLNoga"],
                "P. Noga": data["TluszczPNoga"],
                "Niechciany tłuszcz": data["NiechcianyTluszcz"],
            }]), use_container_width=True)

        with st.expander("Woda + Inne"):
            st.dataframe(pd.DataFrame([{
                "Waga": data["Waga"],
                "Masa wody": data["MasaWody"],
                "Procent wody": data["ProcentWody"],
                "Notatka": data.get("Notatka", "")
            }]), use_container_width=True)

    def display_interpretation(self):
        with st.expander("📊 Porównanie do sylwetki idealnej"):
            last_entry = self.combined_data[-1]
            ideal_comparison = compare_to_ideal(last_entry)
            for line in ideal_comparison:
                st.markdown(f"- {line}")

        if len(self.combined_data) < 2:
            st.info("Potrzeba przynajmniej dwóch pomiarów do wygenerowania analizy.")
            return

        with st.expander("📈 Trendy wskaźników"):
            ratio_trends = analyze_combined_ratios_over_time(self.combined_data)
            for line in ratio_trends:
                st.markdown(f"- {line}")
               
        analysis_text = generate_combined_analysis(self.combined_data)
        st.markdown(analysis_text)
