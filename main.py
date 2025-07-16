import streamlit as st
import pandas as pd
from views.training import TrainingInputForm, TrainingHistoryView
from views.body import BodyMeasurementsForm, BodyMeasurementsHistory
from controllers.training_controller import TrainingController
from controllers.body_controller import BodyController
from storage.training_storage import fetch_all_exercises, fetch_exercise_groups
from analytics.volume_analysis import calculate_volume_per_muscle

st.set_page_config(page_title="Fitness Tracker", layout="wide")

# Inicjalizacja
exercises_raw = fetch_all_exercises()
exercises_group = fetch_exercise_groups()
exercises_dict = {row.Nazwa: row.Id for row in exercises_raw}
training_form = TrainingInputForm(exercises_dict)
training_history = TrainingHistoryView()
body_form = BodyMeasurementsForm()
body_history = BodyMeasurementsHistory()

training_ctrl = TrainingController()
body_ctrl = BodyController()
exercise_main_groups, exercise_detail_groups = training_ctrl.map_exercises_to_muscle_groups(exercises_group)

# Nawigacja
menu = st.sidebar.radio("Menu", ["Dodaj trening", "Historia treningów", "Dodaj pomiary", "Historia pomiarów"])

match menu:
    case "Dodaj trening":
        training = training_form.input_training()
        if st.button("Zapisz trening"):
            training_ctrl.save_training(training)
            st.success("Zapisano trening.")
    
    case "Historia treningów":
        history = training_ctrl.get_training_history()
        df = pd.DataFrame([{
            "Data": row.Data,
            "Cwiczenie": row.Cwiczenie,
            "Powtorzenia": row.Powtorzenia,
            "Ciezar": row.Ciezar} for row in history])
        volume_main = calculate_volume_per_muscle(df, exercise_main_groups)

        tab1, tab2, tab3 = st.tabs(["Historia treningów", "Objętość treningowa", "Progresja siłowa"])

        with tab1:
            training_history.display_training_history()
        
        with tab2:
            date_range = (df['Data'].min(), df['Data'].max())
            training_history.display_volume_charts(volume_main, "Partie główne", date_range)


    case "Dodaj pomiary":
        data = body_form.input_body_measurements()
        if st.button("Zapisz pomiary"):
            body_ctrl.save_measurements(data)
            st.success("Zapisano pomiary.")

    case "Historia pomiarów":
        measurements = body_ctrl.get_measurements()
        body_history.display_history(measurements)