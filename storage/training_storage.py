from logic.database import Database
from config.db_config import CONNECTION_STRING

def save_training(training):
    db = Database(CONNECTION_STRING)
    try:
        trening_id = db.insert_training(training.data)
        for ex in training.exercises:
            trening_cwiczenie_id = db.insert_training_exercise(trening_id, ex.exercise_id)
            for seria in ex.series:
                db.insert_training_series(trening_cwiczenie_id, seria.powtorzenia, seria.ciezar)
    finally:
        db.close()

def load_training_history():
    db = Database(CONNECTION_STRING)
    try:
        return db.fetch_training_history()
    finally:
        db.close()

def fetch_all_exercises():
    db = Database(CONNECTION_STRING)
    try:
        return db.fetch_exercises()
    finally:
        db.close()