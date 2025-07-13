import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
from analytics import summarize_measurements

class BodyMeasurementsView:
    def __init__(self):
        self.metric_units = {
            "Waga": "Waga [kg]",
            "Klatka piersiowa": "Klatka piersiowa [cm]",
            "Talia": "Talia [cm]",
            "Biodra": "Biodra [cm]",
            "Udo": "Udo [cm]",
            "Łydka": "Łydka [cm]",
            "Ramie": "Ramię [cm]",
            "Masa mięśniowa": "Masa mięśniowa [kg]",
            "Masa tłuszczowa": "Masa tłuszczowa [kg]",
            "Tkanka tłuszczowa": "Tkanka tłuszczowa [%]",
            "Woda ciała": "Woda ciała [kg]"}

    def input_body_measurements(self):
        st.header("Dodaj pomiary ciała")
        data = st.date_input("Data pomiaru:", datetime.date.today())

        podstawowe = [
            "Waga (kg)", "Klatka piersiowa (cm)", "Talia (cm)", "Brzuch (cm)",
            "Biodra (cm)", "Udo (cm)", "Łydka (cm)", "Ramię/Biceps (cm)"
        ]
        values = [st.number_input(k, min_value=0.0, step=0.1) for k in podstawowe]

        st.subheader("Skład ciała (opcjonalnie)")
        masa_miesniowa = st.number_input("Masa mięśniowa (kg)", min_value=0.0, step=0.1)
        masa_tluszczowa = st.number_input("Masa tłuszczowa (kg)", min_value=0.0, step=0.1)
        tkanka_tluszczowa = st.number_input("Tkanka tłuszczowa (%)", min_value=0.0, step=0.1)
        woda = st.number_input("Woda w ciele (kg)", min_value=0.0, step=0.1)
        notatka = st.text_input("Notatka (opcjonalnie)")

        return (data, *values, masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa, woda, notatka)

    def display_history(self, measurements):
        st.title("Historia pomiarów ciała")

        if not measurements:
            st.info("Brak pomiarów do wyświetlenia.")
            return

        df = pd.DataFrame([{
            "Data": m["DataPomiaru"],
            "Waga": m["Waga"],
            "Klatka piersiowa": m["KlatkaPiersiowa"],
            "Talia": m["Talia"],
            "Biodra": m["Biodra"],
            "Udo": m["Udo"],
            "Łydka": m["Lydka"],
            "Ramie": m["Ramie"],
            "Masa mięśniowa": m["MasaMiesniowa"],
            "Masa tłuszczowa": m["MasaTluszczowa"],
            "Tkanka tłuszczowa": m["TkankaTluszczowa"],
            "Woda ciała": m["WodaCiala"],
        } for m in measurements])

        df["Data"] = pd.to_datetime(df["Data"])
        metrics = [col for col in df.columns if col != "Data"]
        selected_metric = st.radio("Wybierz parametr:", metrics, horizontal=True)

        summary = summarize_measurements(df, selected_metric)
        if not summary:
            st.warning("Brak danych do analizy.")
            return

        min_val = summary["min"]
        max_val = summary["max"]
        avg_val = summary["avg"]
        percent_change = summary["percent_change"]
        trend_icon = summary["trend_icon"]
        full_metric_label = self.metric_units[selected_metric]

        subtitle = (f"Średnia: {avg_val:.2f}, Min: {min_val:.2f}, Max: {max_val:.2f}"
                    f"| Zmiana: {percent_change:+.2f}% {trend_icon}")

        fig = px.line(
                        df,
                        x="Data",
                        y=selected_metric,
                        markers=True,
                        title=f"{full_metric_label}<br><sup>{subtitle}</sup>",
                        labels={"Data": "Data", selected_metric: selected_metric})

        fig.update_layout(title={"text": f"{full_metric_label}<br><sup>{subtitle}</sup>", "x": 0.5, "xanchor": "center", "yanchor": "top",
                                 "font": {"size": 30}},
                        xaxis_title="Data",
                        yaxis_title=selected_metric,
                        template="plotly_white",
                        hovermode="x unified",
                        margin=dict(t=100),
                        xaxis_tickformat="%d-%m")
        
        st.plotly_chart(fig, use_container_width=True)
