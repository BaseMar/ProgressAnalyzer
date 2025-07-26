from logic.database import Database
from config.db_config import CONNECTION_STRING

def insert_body_composition(data_tuple):
    db = Database(CONNECTION_STRING)
    try:
        db.insert_body_composition(*data_tuple)
    finally:
        db.close()

def fetch_body_composition_history():
    db = Database(CONNECTION_STRING)
    try:
        return db.fetch_body_composition_history()
    finally:
        db.close()
