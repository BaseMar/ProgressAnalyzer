import streamlit as st
from models import Series, TrainingExercise, Training
import datetime

def input_training(exercises_dict):
    """Wyświetlenie okna z dodawanie treningu"""

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

def display_training_history(history_data):
    """Wyświetlanie okna z historią treningów"""

    st.title("Historia treningów")

    if not history_data:
        st.info("Brak zapisanych treningów")
        return
    
    training = {}
    for row in history_data:
        data = row.Data.strftime('%Y-%m-%d')
        exercise = row.Cwiczenie
        powt, kg = row.Powtorzenia, row.Ciezar
        
        if data not in training:
            training[data] = {}
        
        if exercise not in training[data]:
            training[data][exercise] = []

        training[data][exercise].append((powt, kg))


    for data, exercise in sorted(training.items(), reverse=True):
        st.subheader(f"{data}")
        for nazwa, serie in exercise.items():
            serie_str = " | ".join([f"{i+1} Seria: {powt} powt., {kg} kg" for i, (powt, kg) in enumerate(serie)])
            st.markdown(f"**{nazwa}** ➔ {serie_str}")