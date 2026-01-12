import logging
from typing import Any, Dict, List
from datetime import time
import pandas as pd
from sqlalchemy import select, text

from db.connection import get_engine
from db.queries import (
    get_all_sets,
    get_body_composition,
    get_body_measurements,
    get_exercise_id_by_name,
    get_exercises,
    get_workout_sessions,
    insert_body_composition,
    insert_body_measurements,
    insert_exercise,
    insert_session,
    insert_workout_exercise,
    insert_workout_set,
)

logger = logging.getLogger(__name__)


class DataManager:
    """Database access wrapper that returns query results as Pandas DataFrames.

    This class encapsulates calls to the lower-level SQL query helpers and exposes
    convenience methods used by the application UI and services.
    """

    def __init__(self):
        """Initialize the DataManager and create/cache the DB engine."""
        self.engine = get_engine()

    def load_sessions(self) -> pd.DataFrame:
        """Load all workout sessions from the database."""
        return get_workout_sessions(self.engine)

    def load_exercises(self) -> pd.DataFrame:
        """Load all exercises from the database."""
        return get_exercises(self.engine)

    def load_sets(self) -> pd.DataFrame:
        """Load all workout sets with detailed information."""
        return get_all_sets(self.engine)

    def load_body_data(self) -> dict[str, pd.DataFrame]:
        """Load body measurements and body composition data.

        Returns a dict with keys 'measurements' and 'composition', each mapped to
        a DataFrame.
        """
        return {
            "measurements": get_body_measurements(self.engine),
            "composition": get_body_composition(self.engine),
        }

    def add_exercise(self, name: str, category: str, body_part: str) -> bool:
        """Insert a new exercise into the database.

        Returns True on success, False on database error.
        """
        try:
            insert_exercise(self.engine, name, category, body_part)
            return True
        except Exception as e:
            logger.exception("add_exercise failed: %s", e)
            return False

    def add_full_session(self, session_date: Any, notes: str, exercise_name: str, sets_data: List[Dict[str, Any]], session_start: time, session_end: time ) -> bool:
        """Insert a complete workout session including exercise and sets.

        Returns True on success or re-raises the exception if the operation fails.
        """
        try:
            engine = self.engine
            with engine.begin() as conn:
                # check existing session
                qry = text(
                    "SELECT SessionID FROM WorkoutSessions WHERE CAST(SessionDate AS DATE) = :session_date"
                )
                row = conn.execute(qry, {"session_date": session_date}).fetchone()
                if row:
                    session_id = row[0]
                else:
                    # insert_session should return inserted id (use OUTPUT or RETURNING)
                    insert_q = text(
                        "INSERT INTO WorkoutSessions (SessionDate, Notes, StartTime, EndTime) OUTPUT INSERTED.SessionID  VALUES (:date, :notes, :start_time, :end_time)"
                    )
                    session_id = conn.execute(
                        insert_q, {"date": session_date, "notes": notes, "start_time": session_start, "end_time": session_end}
                    ).scalar()

                # get exercise id
                ex_id_q = text(
                    "SELECT ExerciseID FROM Exercises WHERE ExerciseName = :name"
                )
                res = conn.execute(ex_id_q, {"name": exercise_name}).fetchone()
                if not res:
                    raise ValueError("Exercise not found")
                exercise_id = res[0]

                # insert workout exercise and get id
                insert_we = text(
                    "INSERT INTO WorkoutExercises (SessionID, ExerciseID) OUTPUT INSERTED.WorkoutExerciseID VALUES (:sid, :eid)"
                )
                workout_ex_id = conn.execute(
                    insert_we, {"sid": session_id, "eid": exercise_id}
                ).scalar()

                # insert sets
                for idx, s in enumerate(sets_data, start=1):
                    ins_set = text(
                        "INSERT INTO WorkoutSets (WorkoutExerciseID, SetNumber, Repetitions, Weight, RIR) VALUES (:weid, :num, :reps, :weight, :rir)"
                    )
                    conn.execute(
                        ins_set,
                        {
                            "weid": workout_ex_id,
                            "num": idx,
                            "reps": s["reps"],
                            "weight": s["weight"],
                            "rir": s["rir"]
                        },
                    )
            return True
        except Exception:
            logger.exception("add_full_session failed")
            raise

    def add_body_measurements(self, data: dict) -> bool:
        """Insert body measurement records into the database.

        Returns True on success, False on database error.
        """
        try:
            insert_body_measurements(self.engine, data)
            return True
        except Exception as e:
            logger.exception("add_body_measurements failed: %s", e)
            return False

    def add_body_composition(self, data: dict) -> bool:
        """Insert body composition records into the database.

        Returns True on success, False on database error.
        """
        try:
            insert_body_composition(self.engine, data)
            return True
        except Exception as e:
            logger.exception("add_body_composition failed: %s", e)
            return False
