import streamlit as st
import datetime
from models import Series, TrainingExercise, Training
import pandas as pd
from analytics import filter_training_data

class TrainingView:
    def __init__(self, exercises_dict):
        self.exercises_dict = exercises_dict

    def input_training(self):
        """Wyświetlenie formularza do dodawania treningu"""

        st.title("Dodaj trening")

        data_treningu = st.date_input("Data treningu:", datetime.date.today())
        exercise_name = st.selectbox("Wybierz ćwiczenie:", list(self.exercises_dict.keys()))
        exercise_id = self.exercises_dict[exercise_name]
        num_series = st.number_input("Ile serii chcesz dodać?", min_value=1, max_value=10, value=3)
        series_list = []

        for i in range(num_series):
            col1, col2 = st.columns(2)
            with col1:
                reps = st.number_input(f"Powtórzenia - Seria {i+1}:", min_value=1, value=10, key=f"reps_{i}")
            with col2:
                weight = st.number_input(f"Ciężar (kg) - Seria {i+1}:", min_value=0.0, value=20.0, key=f"weight_{i}")
            series_list.append(Series(powtorzenia=reps, ciezar=weight))
        exercises = [TrainingExercise(exercise_id=exercise_id, series=series_list)]

        return Training(data=data_treningu, exercises=exercises)
    
    def display_training_history(self, history_data):
        """Wyświetlanie okna z historią treningów"""

        st.title("Historia treningów")

        if not history_data:
            st.info("Brak zapisanych treningów")
            return
        
        data = [{
        'Data': row.Data,
        'Cwiczenie': row.Cwiczenie,
        'Powtorzenia': row.Powtorzenia,
        'Ciezar': row.Ciezar} for row in history_data]

        df = pd.DataFrame([{
            'Data': row.Data,
            'Cwiczenie': row.Cwiczenie,
            'Powtorzenia': row.Powtorzenia,
            'Ciezar': row.Ciezar} for row in history_data])
        
        df['Data'] = pd.to_datetime(df["Data"])
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
                    f"{i+1} Seria: {row.Powtorzenia} powt., {row.Ciezar} kg"
                    for i, row in ex_group.iterrows()
                )
                st.markdown(f"**{exercise}** ➔ {series_str}")
            st.markdown("---")