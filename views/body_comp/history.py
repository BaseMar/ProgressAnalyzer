import streamlit as st
import pandas as pd
import plotly.express as px
from analytics.body_analysis import summarize_measurements

class BodyCompositionHistory:
    def __init__(self):
        self.metric_units = {
            "Waga": "Waga [kg]",
            "Masa mięśniowa": "Masa mięśniowa [kg]",
            "Masa tłuszczowa": "Masa tłuszczowa [kg]",
            "% tkanki tłuszczowej": "% tkanki tłuszczowej",
            "% wody": "% wody",
            "Masa wody": "Masa wody [kg]",
            "Mięśnie tułów": "Mięśnie tułów [kg]",
            "Mięśnie lewa ręka": "Mięśnie lewa ręka [kg]",
            "Mięśnie prawa ręka": "Mięśnie prawa ręka [kg]",
            "Mięśnie lewa noga": "Mięśnie lewa noga [kg]",
            "Mięśnie prawa noga": "Mięśnie prawa noga [kg]",
            "Tłuszcz tułów": "Tłuszcz tułów [%]",
            "Tłuszcz lewa ręka": "Tłuszcz lewa ręka [%]",
            "Tłuszcz prawa ręka": "Tłuszcz prawa ręka [%]",
            "Tłuszcz lewa noga": "Tłuszcz lewa noga [%]",
            "Tłuszcz prawa noga": "Tłuszcz prawa noga [%]",
            "Niechciany tłuszcz": "Niechciany tłuszcz"
        }

    def display_history(self, data):
        st.title("Historia składu ciała")

        if not data:
            st.info("Brak danych do wyświetlenia.")
            return

        df = self._prepare_dataframe(data)
        metrics = [col for col in df.columns if col != "Data"]
        selected_metric = st.radio("Wybierz parametr:", metrics, horizontal=True)

        summary = summarize_measurements(df, selected_metric)
        if not summary:
            st.warning("Brak danych do analizy.")
            return

        subtitle = (
            f"Średnia: {summary['avg']:.2f}, Min: {summary['min']:.2f}, Max: {summary['max']:.2f} "
            f"| Zmiana: {summary['percent_change']:+.2f}% {summary['trend_icon']}"
        )

        fig = px.line(
            df,
            x="Data",
            y=selected_metric,
            markers=True,
            title=f"{self.metric_units.get(selected_metric, selected_metric)}<br><sup>{subtitle}</sup>",
            labels={"Data": "Data", selected_metric: selected_metric},
        )

        fig.update_layout(title={"x": 0.5, "xanchor": "center", "yanchor": "top","font": {"size": 30}},
                        xaxis_title="Data",
                        yaxis_title=selected_metric,
                        template="plotly_white",
                        hovermode="x unified",
                        margin=dict(t=100),
                        xaxis_tickformat="%d-%m")

        st.plotly_chart(fig, use_container_width=True)

    def _prepare_dataframe(self, raw):
        df = pd.DataFrame([{
            "Data": m["DataPomiaru"],
            "Waga": m["Waga"],
            "Masa mięśniowa": m["MasaMiesniowa"],
            "Masa tłuszczowa": m["MasaTluszczowa"],
            "% tkanki tłuszczowej": m["TkankaTluszczowa"],
            "% wody": m["ProcentWody"],
            "Masa wody": m["MasaWody"],
            "Mięśnie tułów": m["MiesnieTulow"],
            "Mięśnie lewa ręka": m["MiesnieLRece"],
            "Mięśnie prawa ręka": m["MiesniePRece"],
            "Mięśnie lewa noga": m["MiesnieLNoga"],
            "Mięśnie prawa noga": m["MiesniePNoga"],
            "Tłuszcz tułów": m["TluszczTulow"],
            "Tłuszcz lewa ręka": m["TluszczLRece"],
            "Tłuszcz prawa ręka": m["TluszczPRece"],
            "Tłuszcz lewa noga": m["TluszczLNoga"],
            "Tłuszcz prawa noga": m["TluszczPNoga"],
            "Niechciany tłuszcz": m["NiechcianyTluszcz"]
        } for m in raw])
        df["Data"] = pd.to_datetime(df["Data"])
        return df
