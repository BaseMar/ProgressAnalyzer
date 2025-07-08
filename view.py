import streamlit as st
from models import Series, TrainingExercise, Training
import datetime

def input_training(exercises_dict):
    st.title("Dodaj trening")
    data_treningu = st.date_input("Data treningu:", datetime.date.today())

    exercises = []

    exercise_name = st.selectbox("Wybierz ćwiczenie:", list(exercises_dict.keys()))
    exercise_id = exercises_dict[exercise_name]

    num_series = st.number_input("Ile serii chcesz dodać?", min_value=1, max_value=10, value=3)

    series_list = []
    for i in range(num_series):
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input(f"Powtórzenia - Seria {i+1}:", min_value=1, value=10, key=f"reps_{i}")
        with col2:
            weight = st.number_input(f"Ciężar (kg) - Seria {i+1}:", min_value=0.0, value=20.0, key=f"weight_{i}")
        series_list.append(Series(powtorzenia=reps, ciezar=weight))

    exercises.append(TrainingExercise(exercise_id=exercise_id, series=series_list))

    return Training(data=data_treningu, exercises=exercises)
