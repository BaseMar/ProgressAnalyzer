import pandas as pd
from db.queries import (
    get_workout_sessions,
    get_exercises,
    get_all_sets,
    get_body_measurements,
    get_body_composition,
    insert_exercise,
    insert_session,
    get_exercise_id_by_name,
    insert_workout_exercise,
    insert_workout_set,
    insert_body_measurements,
    insert_body_composition,
)
from db.connection import get_engine
from sqlalchemy import select, text
import logging

logger = logging.getLogger(__name__)

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
        try:
            insert_exercise(self.engine, name, category, body_part)
            return True
        except Exception as e:
            print(f"[ERROR] add_exercise: {e}")
            return False

    def add_full_session(self, session_date, notes, exercise_name, sets_data):
        try:
            engine = self.engine
            with engine.begin() as conn:
                # check existing session
                qry = text("SELECT SessionID FROM WorkoutSessions WHERE CAST(SessionDate AS DATE) = :session_date")
                row = conn.execute(qry, {"session_date": session_date}).fetchone()
                if row:
                    session_id = row[0]
                else:
                    # insert_session should return inserted id (use OUTPUT or RETURNING)
                    insert_q = text("INSERT INTO WorkoutSessions (SessionDate, Notes) OUTPUT INSERTED.SessionID VALUES (:date, :notes)")
                    session_id = conn.execute(insert_q, {"date": session_date, "notes": notes}).scalar()

                # get exercise id
                ex_id_q = text("SELECT ExerciseID FROM Exercises WHERE ExerciseName = :name")
                res = conn.execute(ex_id_q, {"name": exercise_name}).fetchone()
                if not res:
                    raise ValueError("Brak ćwiczenia")
                exercise_id = res[0]

                # insert workout exercise and get id
                insert_we = text("INSERT INTO WorkoutExercises (SessionID, ExerciseID) OUTPUT INSERTED.WorkoutExerciseID VALUES (:sid, :eid)")
                workout_ex_id = conn.execute(insert_we, {"sid": session_id, "eid": exercise_id}).scalar()

                # insert sets
                for idx, s in enumerate(sets_data, start=1):
                    ins_set = text("INSERT INTO WorkoutSets (WorkoutExerciseID, SetNumber, Repetitions, Weight) VALUES (:weid, :num, :reps, :weight)")
                    conn.execute(ins_set, {"weid": workout_ex_id, "num": idx, "reps": s["reps"], "weight": s["weight"]})
            return True
        except Exception:
            logger.exception("add_full_session failed")
            raise

    def add_body_measurements(self, data: dict) -> bool:
        try:
            insert_body_measurements(self.engine, data)
            return True
        except Exception as e:
            print(f"[ERROR] add_body_measurements: {e}")
            return False

    def add_body_composition(self, data: dict) -> bool:
        try:
            insert_body_composition(self.engine, data)
            return True
        except Exception as e:
            print(f"[ERROR] add_body_composition: {e}")
            return False
        