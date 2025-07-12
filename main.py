from database import Database
from TrainingView import TrainingView
from BodyMeasurementsView import BodyMeasurementsView
import streamlit as st

CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-CGQ7P1E\\MSSQLSERVER04;'
    'DATABASE=Excercise;'
    'Trusted_Connection=yes;'
)

def main():
    db = Database(CONNECTION_STRING)
    
    try:
        exercises_raw = db.fetch_exercises()
        exercises_dict = {row.Nazwa: row.Id for row in exercises_raw}
        training_view = TrainingView(exercises_dict)
        body_view = BodyMeasurementsView()
        menu = st.sidebar.radio("Menu",("Dodaj trening", "Historia treningów", "Pomiary ciała", "Historia pomiarów ciała")
    )
        match menu:
            case "Dodaj trening":
                training = training_view.input_training()
                if st.button("Zapisz trening"):
                    try:
                        trening_id = db.insert_training(training.data)
                        for ex in training.exercises:
                            trening_cwiczenie_id = db.insert_training_exercise(trening_id, ex.exercise_id)
                            for ser in ex.series:
                                db.insert_training_series(trening_cwiczenie_id, ser.powtorzenia, ser.ciezar)
                        st.success("Trening został zapisany!")
                    except Exception as e:
                        st.error(f"Wystąpił błąd: {e}")
            
            case "Historia treningów":
                history = db.fetch_training_history()
                training_view.display_training_history(history)
            
            case "Pomiary ciała":
                pomiary = body_view.input_body_measurements()
                if st.button("Zapisz pomiary"):
                    db.insert_body_measurements(*pomiary)
                    st.success("Pomiary zapisane!")

            case "Historia pomiarów ciała":
                measurements = db.fetch_body_measurements()
                body_view.display_history(measurements)
            case _:
                st.header("Witaj w aplikacji")
    finally:
        db.close()

if __name__ == "__main__":
    main()
