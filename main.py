import streamlit as st
from analytics.body_analyzer import BodyAnalyzer
from analytics.data_manager import merge_body_data_with_tolerance
from views.training import TrainingInputForm, TrainingHistoryView
from views.body import BodyMeasurementsForm, BodyMeasurementsHistory
from views.body_comp.input_form import BodyCompositionForm
from controllers.training_controller import TrainingController
from views.body_comp.history import BodyCompositionHistory
from controllers.body_controller import BodyController
from storage.training_storage import fetch_all_exercises, fetch_exercise_groups

st.set_page_config(page_title="Fitness Tracker", layout="wide")

# Inicjalizacja
exercises_raw = fetch_all_exercises()
exercises_group = fetch_exercise_groups()
exercises_dict = {row.Nazwa: row.Id for row in exercises_raw}
training_ctrl = TrainingController()

training_form = TrainingInputForm(exercises_dict)
training_history_view = TrainingHistoryView()
body_form = BodyMeasurementsForm()
body_history = BodyMeasurementsHistory()
body_comp = BodyCompositionForm()
composition_history_view = BodyCompositionHistory()
body_ctrl = BodyController()

exercise_main_groups, exercise_detail_groups = training_ctrl.map_exercises_to_muscle_groups(exercises_group)
training_df = training_ctrl.get_training_history()
mapped_main_groups_df = training_ctrl.map_training_to_muscle_groups(training_df, exercise_main_groups)
body_measurements = body_ctrl.get_measurements()
body_composition = body_ctrl.get_composition_history()
body_analyzer = BodyAnalyzer(merge_body_data_with_tolerance(body_measurements, body_composition))

# Nawigacja
menu = st.sidebar.radio("Menu", ["Formularze", "Historia treningów", "Historia pomiarów ciała"])

match menu:
    case "Formularze":
        tab1, tab2, tab3 = st.tabs(["Dodaj trening", "Dodaj pomiary", "Dodaj skład ciała"])

        with tab1:
            training = training_form.input_training()
            if st.button("Zapisz trening"):
                training_ctrl.save_training(training)
                st.success("Zapisano trening.")
        
        with tab2:
            data = body_form.input_body_measurements()
            if st.button("Zapisz pomiary"):
                body_ctrl.save_measurements(data)
                st.success("Zapisano pomiary.")
        
        with tab3:
            data = body_comp.input_composition()
            if st.button("Zapisz skład ciała"):
                body_ctrl.save_composition(data)
                st.success("Zapisano analizę składu ciała.")

    case "Historia treningów":
        tab1, tab2 = st.tabs(["Historia treningów", "Analiza treningów"])
        with tab1:
            training_history_view.display_training_history()
        
        with tab2:
            with st.expander("📊 Analiza intensywności"):
                training_history_view.show_intensity_analysis(mapped_main_groups_df)

    case "Historia pomiarów ciała":
        tab1, tab2 = st.tabs(["Pomiar ciała w czasie", "Skład ciała w czasie"])

        with tab1:
            measurements = body_ctrl.get_measurements()
            body_history.display_history(measurements)
        
        with tab2:
            data = body_ctrl.get_composition_history()
            composition_history_view.display_history(data)