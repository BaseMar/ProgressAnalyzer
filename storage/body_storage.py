from logic.database import Database
from config.db_config import CONNECTION_STRING

def insert_body_measurements(data_tuple):
    db = Database(CONNECTION_STRING)
    try:
        db.insert_body_measurements(*data_tuple)
    finally:
        db.close()

def fetch_body_measurements():
    db = Database(CONNECTION_STRING)
    try:
        return db.fetch_body_measurements()
    finally:
        db.close()