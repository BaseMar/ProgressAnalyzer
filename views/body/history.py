import streamlit as st
import pandas as pd
import plotly.express as px
from analytics.body_analyzer import BodyAnalyzer

class BodyMeasurementsHistory(BodyAnalyzer):
    def __init__(self):
        self.metric_units = {
            "Klatka piersiowa": "Klatka piersiowa [cm]",
            "Talia": "Talia [cm]",
            "Biodra": "Biodra [cm]",
            "Udo": "Udo [cm]",
            "Łydka": "Łydka [cm]",
            "Ramie": "Ramię [cm]",}
    
    def display_history(self, measurements):
        st.title("Historia pomiarów ciała")

        if not measurements:
            st.info("Brak pomiarów do wyświetlenia.")
            return
        
        df = self._prepare_dataframe(measurements)

        metrics = [col for col in df.columns if col != "Data"]
        selected_metric = st.radio("Wybierz parametr:", metrics, horizontal=True)

        summary = self.summarize_measurements(df, selected_metric)
        if not summary:
            st.warning("Brak danych do analizy.")
            return

        subtitle = (
            f"Średnia: {summary['avg']:.2f}, Min: {summary['min']:.2f}, Max: {summary['max']:.2f}"
            f" | Zmiana: {summary['percent_change']:+.2f}% {summary['trend_icon']}")

        fig = px.line(
                        df,
                        x="Data",
                        y=selected_metric,
                        markers=True,
                        title=f"{self.metric_units[selected_metric]}<br><sup>{subtitle}</sup>",
                        labels={"Data": "Data", selected_metric: selected_metric})

        fig.update_layout(title={"x": 0.5, "xanchor": "center", "yanchor": "top","font": {"size": 30}},
                        xaxis_title="Data",
                        yaxis_title=selected_metric,
                        template="plotly_white",
                        hovermode="x unified",
                        margin=dict(t=100),
                        xaxis_tickformat="%d-%m")
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _prepare_dataframe(self, raw_measurements):
        df = pd.DataFrame([{
            "Data": m["DataPomiaru"],
            "Klatka piersiowa": m["KlatkaPiersiowa"],
            "Talia": m["Talia"],
            "Biodra": m["Biodra"],
            "Udo": m["Udo"],
            "Łydka": m["Lydka"],
            "Ramie": m["Ramie"],
        } for m in raw_measurements])
        df["Data"] = pd.to_datetime(df["Data"])
        return df