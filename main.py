from database import Database
from view import input_training, display_training_history, input_body_measurements, display_body_measurements_history
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

        menu = st.sidebar.radio("Menu",("Dodaj trening", "Historia treningów", "Pomiary ciała", "Historia pomiarów ciała")
    )
        match menu:
            case "Dodaj trening":
                training = input_training(exercises_dict)
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
                    finally:
                        db.close()
            
            case "Historia treningów":
                history = db.fetch_training_history()
                display_training_history(history)
            
            case "Pomiary ciała":
                pomiary = input_body_measurements()
                if st.button("Zapisz pomiary"):
                    db.insert_body_measurements(*pomiary)
                    st.success("Pomiary zapisane!")

            case "Historia pomiarów ciała":
                measurements = db.fetch_body_measurements()
                display_body_measurements_history(measurements)
            case _:
                st.header("Witaj w aplikacji")
    finally:
        db.close()

if __name__ == "__main__":
    main()
