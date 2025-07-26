import streamlit as st
import pandas as pd

TREND_ICONS = lambda diff: "🔺" if diff > 0 else "🔻" if diff < 0 else "➖"

class BodyCompositionCompareView:
    def display_comparison(self, history):
        st.title("Porównanie składu ciała")

        if len(history) < 2:
            st.warning("Potrzebujesz co najmniej dwóch pomiarów, aby wykonać porównanie.")
            return

        df = pd.DataFrame(history)
        df["DataPomiaru"] = pd.to_datetime(df["DataPomiaru"])
        df = df.sort_values("DataPomiaru")

        dates = df["DataPomiaru"].dt.strftime("%Y-%m-%d").tolist()
        col1, col2 = st.columns(2)
        with col1:
            selected_date_1 = st.selectbox("Wybierz datę początkową", dates, index=0)
        with col2:
            selected_date_2 = st.selectbox("Wybierz datę końcową", dates, index=len(dates)-1)

        if selected_date_1 == selected_date_2:
            st.info("Wybierz dwie różne daty do porównania.")
            return

        row1 = df[df["DataPomiaru"] == pd.to_datetime(selected_date_1)].iloc[0]
        row2 = df[df["DataPomiaru"] == pd.to_datetime(selected_date_2)].iloc[0]

        fields = [
            ("Waga", "kg"),
            ("MasaMiesniowa", "kg"),
            ("MasaTluszczowa", "kg"),
            ("TkankaTluszczowa", "%"),
            ("ProcentWody", "%"),
            ("MasaWody", "kg"),
            ("MiesnieTulow", "kg"),
            ("MiesnieLRece", "kg"),
            ("MiesniePRece", "kg"),
            ("MiesnieLNoga", "kg"),
            ("MiesniePNoga", "kg"),
            ("TluszczTulow", "kg"),
            ("TluszczLRece", "kg"),
            ("TluszczPRece", "kg"),
            ("TluszczLNoga", "kg"),
            ("TluszczPNoga", "kg"),
            ("NiechcianyTluszcz", "kg"),
        ]

        st.subheader("Porównanie wartości")
        table_data = []
        for field, unit in fields:
            val1 = row1[field]
            val2 = row2[field]
            diff = val2 - val1
            percent = (diff / val1 * 100) if val1 else 0
            icon = TREND_ICONS(diff)

            table_data.append({
                "Parametr": field,
                f"{selected_date_1}": f"{val1:.2f} {unit}",
                f"{selected_date_2}": f"{val2:.2f} {unit}",
                "Zmiana": f"{diff:+.2f} {unit}",
                "%": f"{percent:+.1f}%",
                "Trend": icon
            })

        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
