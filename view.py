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

def input_body_measurements():
    st.header("Dodaj pomiary ciała")

    data = st.date_input("Data pomiaru:", datetime.date.today())
    waga = st.number_input("Waga (kg)", min_value=0.0, step=0.1)
    klatka = st.number_input("Klatka piersiowa (cm)", min_value=0.0, step=0.1)
    talia = st.number_input("Talia (cm)", min_value=0.0, step=0.1)
    brzuch = st.number_input("Brzuch (cm)", min_value=0.0, step=0.1)
    biodra = st.number_input("Biodra (cm)", min_value=0.0, step=0.1)
    udo = st.number_input("Udo (cm)", min_value=0.0, step=0.1)
    lydka = st.number_input("Łydka (cm)", min_value=0.0, step=0.1)
    ramie = st.number_input("Ramię/Biceps (cm)", min_value=0.0, step=0.1)

    st.subheader("Skład ciała (opcjonalnie)")
    masa_miesniowa = st.number_input("Masa mięśniowa (%)", min_value=0.0, step=0.1)
    masa_tluszczowa = st.number_input("Masa tłuszczowa (kg)", min_value=0.0, step=0.1)
    tkanka_tluszczowa = st.number_input("Tkanka tłuszczowa (%)", min_value=0.0, step=0.1)
    woda = st.number_input("Woda w ciele (%)", min_value=0.0, step=0.1)

    notatka = st.text_input("Notatka (opcjonalnie)")

    return (data, waga, klatka, talia, brzuch, biodra, udo, lydka, ramie,
            masa_miesniowa, masa_tluszczowa, tkanka_tluszczowa, woda, notatka)

def display_body_measurements_history(measurements):
    st.header("Historia pomiarów ciała")

    for row in measurements:
        st.subheader(f"{row.DataPomiaru.strftime('%Y-%m-%d')}")
        st.write(f"💪 Waga: {row.Waga} kg | Klatka: {row.KlatkaPiersiowa} cm | Talia: {row.Talia} cm | Brzuch: {row.Brzuch} cm")
        st.write(f"Biodra: {row.Biodra} cm | Udo: {row.Udo} cm | Łydka: {row.Lydka} cm | Ramię: {row.Ramie} cm")
        st.write(f"Masa mięśniowa: {row.MasaMiesniowa}% | Masa tłuszczowa: {row.MasaTluszczowa} kg | Tkanka tłuszczowa: {row.TkankaTluszczowa}% | Woda: {row.WodaCiala}%")
        if row.Notatka:
            st.write(f"📝 {row.Notatka}")
        st.markdown("---")
