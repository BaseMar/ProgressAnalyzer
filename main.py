import streamlit as st
from views.training import TrainingInputForm, TrainingHistoryView
from views.body import BodyMeasurementsForm, BodyMeasurementsHistory
from controllers.training_controller import TrainingController
from controllers.body_controller import BodyController
from storage.training_storage import fetch_all_exercises

st.set_page_config(page_title="Fitness Tracker", layout="wide")

# Inicjalizacja
exercises_raw = fetch_all_exercises()
exercises_dict = {row.Nazwa: row.Id for row in exercises_raw}
training_form = TrainingInputForm(exercises_dict)
training_history = TrainingHistoryView()
body_form = BodyMeasurementsForm()
body_history = BodyMeasurementsHistory()

training_ctrl = TrainingController()
body_ctrl = BodyController()

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
        training_history.display_training_history()

    case "Dodaj pomiary":
        data = body_form.input_body_measurements()
        if st.button("Zapisz pomiary"):
            body_ctrl.save_measurements(data)
            st.success("Zapisano pomiary.")

    case "Historia pomiarów":
        measurements = body_ctrl.get_measurements()
        body_history.display_history(measurements)