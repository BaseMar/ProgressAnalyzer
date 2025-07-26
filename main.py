import streamlit as st
import pandas as pd
from views.training import TrainingInputForm, TrainingHistoryView
from views.body import BodyMeasurementsForm, BodyMeasurementsHistory
from views.body_comp.input_form import BodyCompositionForm
from views.body_comp.compare import BodyCompositionCompareView
from controllers.sklad_controller import BodyCompositionController
from controllers.training_controller import TrainingController
from views.body_comp.history import BodyCompositionHistory
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
body_comp = BodyCompositionForm()
composition_history_view = BodyCompositionHistory()
body_comp_view = BodyCompositionCompareView()

training_ctrl = TrainingController()
body_ctrl = BodyController()
body_comp_ctrl = BodyCompositionController()
exercise_main_groups, exercise_detail_groups = training_ctrl.map_exercises_to_muscle_groups(exercises_group)

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
                body_comp_ctrl.save_composition(data)
                st.success("Zapisano analizę składu ciała.")

    case "Historia treningów":
        history = training_ctrl.get_training_history()
        df = pd.DataFrame([{
            
            "Data": row.Data,
            "Cwiczenie": row.Cwiczenie,
            "Powtorzenia": row.Powtorzenia,
            "Ciezar": row.Ciezar} for row in history])
        volume_main = calculate_volume_per_muscle(df, exercise_main_groups)

        tab1, tab2, tab3, tab4 = st.tabs(["Historia treningów", "Objętość treningowa", "Progresja siłowa", "Raport tygodniowy"])

        with tab1:
            training_history.display_training_history()
        
        with tab2:
            date_range = (df['Data'].min(), df['Data'].max())
            training_history.display_volume_charts(volume_main, "Partie główne", date_range)

        with tab3:
            training_history.display_strength_progression(df)
        
        with tab4:
            exercise_groups_dict = {row.Nazwa: row.PartieGlowne for row in exercises_group}
            training_history.display_weekly_series_report(df, exercise_groups_dict)

    case "Historia pomiarów ciała":
        tab1, tab2, tab3 = st.tabs(["Pomiar ciała", "Skład ciała", "Analiza porównawcza"])

        with tab1:
            measurements = body_ctrl.get_measurements()
            body_history.display_history(measurements)
        
        with tab2:
            data = body_comp_ctrl.get_composition_history()
            composition_history_view.display_history(data)
        
        with tab3:
            data = body_comp_ctrl.get_composition_history()
            body_comp_view.display_comparison(data)
