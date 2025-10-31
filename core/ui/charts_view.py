import streamlit as st
import pandas as pd

class ChartsView:
    """
    Klasa odpowiedzialna za prezentację wykresów w dashboardzie.
    """

    @staticmethod
    def display_intensity_chart(analytics):
        """Wyświetla wykres średniej intensywności tygodniowej."""
        st.subheader("Średnia intensywność tygodniowa")

        df_intensity = analytics.weekly_agg("Intensity", agg_func="mean")
        if isinstance(df_intensity, dict):
            st.info("Brak danych do wyświetlenia wykresu intensywności.")
            return

        st.line_chart(df_intensity, x="Week", y="Intensity")

    @staticmethod
    def display_volume_chart(analytics):
        """Wyświetla wykres łącznej objętości tygodniowej."""
        st.subheader("Łączna objętość tygodniowa")

        df_volume = analytics.df_sets.copy()
        df_volume["Week"] = df_volume["SessionDate"].dt.isocalendar().week
        df_volume["Year"] = df_volume["SessionDate"].dt.isocalendar().year
        weekly_volume = (
            df_volume.groupby(["Year", "Week"])["Volume"]
            .sum()
            .reset_index()
            .sort_values(["Year", "Week"])
        )

        if weekly_volume.empty:
            st.info("Brak danych do wyświetlenia wykresu objętości.")
            return

        st.bar_chart(weekly_volume, x="Week", y="Volume")

    @staticmethod
    def render(analytics):
        """
        Renderuje wszystkie wykresy w dashboardzie głównym.
        """
        st.divider()
        st.header("Analiza treningowa")
        ChartsView.display_intensity_chart(analytics)
        ChartsView.display_volume_chart(analytics)
