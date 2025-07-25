from logic.database import Database
from config.db_config import CONNECTION_STRING

class BodyCompositionStorage:
    @staticmethod
    def insert_body_composition(self):
        db = Database(CONNECTION_STRING)
        self.db.insert_body_composition()

    