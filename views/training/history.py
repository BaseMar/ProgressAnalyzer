import streamlit as st
import pandas as pd
from storage.training_storage import load_training_history
from analytics.data_manager import filter_training_data
from analytics.training_analyzer import calculate_intensity_per_muscle_group, calculate_1rm_per_muscle_group
import plotly.express as px

class TrainingHistoryView:
    def display_training_history(self):
        st.title("Historia treningów")

        df = load_training_history()
        if df.empty:
            st.info("Brak zapisanych treningów")
            return

        min_date, max_date = df['Data'].min(), df['Data'].max()

        date_range = st.date_input("Zakres dat:", [min_date, max_date])
        if len(date_range) != 2:
            st.info("Wybierz pełny zakres dat.")
            return
        date_start, date_end = [pd.to_datetime(d) for d in date_range]

        exercises = sorted(df['Cwiczenie'].unique())
        selected_exercise = st.selectbox("Ćwiczenie (opcjonalnie):", ["Wszystkie"] + exercises)

        filtered_df = filter_training_data(df, date_start, date_end, selected_exercise)

        if filtered_df.empty:
            st.warning("Brak treningów dla wybranych filtrów.")
            return

        for date, group in filtered_df.groupby('Data'):
            st.subheader(date.strftime('%Y-%m-%d'))
            for exercise, ex_group in group.groupby('Cwiczenie'):
                series_str = " | ".join(
                    f"Seria: {row.Powtorzenia} powt., {row.Ciezar} kg"
                    for i, row in ex_group.iterrows()
                )
                st.markdown(f"**{exercise}** ➔ {series_str}")
            st.markdown("---")

    def show_intensity_analysis(self, mapped_df):
        st.subheader("📈 Analiza intensywności treningowej")
        
        intensity_df =  calculate_intensity_per_muscle_group(mapped_df)
        exercises = intensity_df['Partia'].unique().tolist()
        selected_groups = st.multiselect("Wybierz partię mięśniową:", exercises, default=exercises[:1], 
                                         key="intensity_multiselect")

        if not selected_groups:
            st.warning("Wybierz przynajmniej jedną grupę mięśniową.")
            return

        filtered_df = intensity_df[intensity_df['Partia'].isin(selected_groups)]

        fig = px.line(
        filtered_df,
        x='Data',
        y='Intensywnosc',
        color='Partia',
        markers=True,
        title='Intensywność treningowa według partii mięśniowych w czasie')
        st.plotly_chart(fig, use_container_width=True)

    def show_strength_progress(self, mapped_df):
        st.subheader("Progres siłowy (1RM) w czasie")

        agg_option = st.radio(
            "Agregacja czasowa:",
            ["Tygodniowo", "Miesięcznie"],
            horizontal=True,
            key="agg_option_strength"
        )
        freq_map = {"Tygodniowo": "W", "Miesięcznie": "M"}

        one_rm_df = calculate_1rm_per_muscle_group(mapped_df, freq=freq_map[agg_option])
        exercises = one_rm_df['Partia'].unique().tolist()
        selected_groups = st.multiselect(
            "Wybierz partię mięśniową:",
            exercises,
            default=exercises[:1],
            key="strength_progress_multiselect"
        )

        if not selected_groups:
            st.warning("Wybierz przynajmniej jedną grupę mięśniową.")
            return

        filtered_df = one_rm_df[one_rm_df['Partia'].isin(selected_groups)]

        fig = px.line(
            filtered_df,
            x='Data',
            y='1RM',
            color='Partia',
            markers=True,
            title=f'Progres siłowy (szacowany 1RM) w czasie – {agg_option.lower()}'
        )
        st.plotly_chart(fig, use_container_width=True)
