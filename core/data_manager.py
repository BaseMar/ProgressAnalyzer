import pandas as pd
from db.queries import (
    get_workout_sessions,
    get_exercises,
    get_all_sets,
    get_body_measurements,
    get_body_composition,
    insert_exercise,
)
from db.connection import get_engine


class DataManager:
    """
    Klasa odpowiedzialna za komunikację z bazą danych (SQL Server przez SQLAlchemy)
    i zwracanie danych jako DataFrame.
    """

    def __init__(self):
        self.engine = get_engine()

    def load_sessions(self) -> pd.DataFrame:
        """Returns list of training session."""
        return get_workout_sessions(self.engine)

    def load_exercises(self) -> pd.DataFrame:
        """Return list of exercises."""
        return get_exercises(self.engine)

    def load_sets(self) -> pd.DataFrame:
        """Return all training sets."""
        return get_all_sets(self.engine)

    def load_body_data(self) -> dict[str, pd.DataFrame]:
        """Return data of body measurements and body composition."""
        return {
            "measurements": get_body_measurements(self.engine),
            "composition": get_body_composition(self.engine),
        }

    def add_exercise(self, name: str, category: str, body_part: str) -> bool:
        """Add new exercise to database."""
        return insert_exercise(self.engine, name, category, body_part)