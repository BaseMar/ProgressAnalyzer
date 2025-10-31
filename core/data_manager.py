import pandas as pd
from db.connection import get_connection
from db.queries import (
    get_workout_sessions,
    get_exercises,
    get_all_sets,
    get_body_measurements,
    get_body_composition,
)

class DataManager:
    """
    Klasa odpowiedzialna za obsługę zapytań do bazy danych
    oraz zwracanie danych w postaci DataFrame.
    """

    def __init__(self):
        self.conn = get_connection()

    def load_sessions(self) -> pd.DataFrame:
        """Zwraca listę sesji treningowych."""
        return get_workout_sessions()

    def load_exercises(self) -> pd.DataFrame:
        """Zwraca listę ćwiczeń dostępnych w bazie."""
        return get_exercises()

    def load_sets(self) -> pd.DataFrame:
        """Zwraca wszystkie wykonane serie treningowe."""
        return get_all_sets()

    def load_body_data(self):
        """Zwraca dane pomiarowe ciała i składu ciała."""
        return {
            "measurements": get_body_measurements(),
            "composition": get_body_composition(),
        }
