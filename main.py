from database import Database
from view import input_training, display_training_history
from models import Training
import streamlit as st

CONNECTION_STRING = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-CGQ7P1E\\MSSQLSERVER04;'
    'DATABASE=Excercise;'
    'Trusted_Connection=yes;'
)

def main():
    db = Database(CONNECTION_STRING)
    
    exercises_raw = db.fetch_exercises()
    exercises_dict = {row.Nazwa: row.Id for row in exercises_raw}

    menu_items = [
    {"label": "🏋️ Dodaj trening", "value": "add"},
    {"label": "📅 Historia treningów", "value": "history"},
    {"label": "⚙️ Ustawienia", "value": "settings"},
        ]
    page = None

    for item in menu_items:
        if st.sidebar.button(item["label"]):
            page = item["value"]

    match page:
        case "add":
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
        
        case "history":
            history = db.fetch_training_history()
            display_training_history(history)
        
        case "settings":
            st.header("Ustawienia")

        case _:
            st.header("Witaj w aplikacji")
            

if __name__ == "__main__":
    main()
