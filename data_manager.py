import logging
from typing import Any, Dict, List
from datetime import date, time
import pandas as pd
from sqlalchemy import text

from db.connection import get_engine
from db.progression import load_normal_workout_recommendations, load_workout_recommendations
from db.training_plans import (
    load_effective_training_plan, load_training_plan_version, load_training_plan_versions, load_training_plans,
    save_training_plan, training_plan_storage_ready,
)
from models.training_plan import TrainingPlanDraft, TrainingPlanVersion
from db.set_classifications import classifications, classification_storage_ready, load_session_sets, save_set_classifications
from db.plan_adherence import adherence_storage_ready, load_plan_adherence, load_plan_performance, save_exercise_match, remove_exercise_match
from db.plan_schedule import (
    plan_schedule_storage_ready, load_scheduled_workouts, load_scheduled_workout_targets,
    load_plan_session_links, assign_scheduled_session, unassign_scheduled_session,
)
from db.queries import (
    delete_workout_session,
    get_all_sets,
    get_body_composition,
    get_body_measurements,
    get_exercises,
    get_sets_raw,
    get_workout_sessions,
    insert_body_composition,
    insert_body_measurements,
    insert_exercise,
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

    def classification_storage_ready(self):
        return classification_storage_ready(self.engine)

    def load_session_sets(self, session_id):
        return load_session_sets(self.engine, session_id)

    def save_set_classifications(self, session_id, values):
        return save_set_classifications(self.engine, session_id, values)

    def plan_schedule_storage_ready(self):
        return plan_schedule_storage_ready(self.engine)

    def adherence_storage_ready(self):
        return adherence_storage_ready(self.engine)

    def load_plan_adherence(self, plan_id, start, end):
        return load_plan_adherence(self.engine, plan_id, start, end)

    def load_plan_performance(self, plan_id, start, end):
        return load_plan_performance(self.engine, plan_id, start, end)

    def load_normal_workout_recommendations(self, plan_id, day_id, scheduled_date, *, as_of, **options):
        return load_normal_workout_recommendations(self.engine, plan_id, day_id, scheduled_date, as_of=as_of, **options)

    def load_workout_recommendations(self, plan_id, day_id, scheduled_date, *, as_of, **options):
        return load_workout_recommendations(self.engine, plan_id, day_id, scheduled_date, as_of=as_of, **options)

    def save_exercise_match(self, session_id, plan_exercise_id, workout_exercise_id):
        return save_exercise_match(self.engine, session_id, plan_exercise_id, workout_exercise_id)

    def remove_exercise_match(self, session_id, plan_exercise_id):
        return remove_exercise_match(self.engine, session_id, plan_exercise_id)

    def load_scheduled_workouts(self, plan_id, start, end):
        return load_scheduled_workouts(self.engine, plan_id, start, end)

    def load_scheduled_workout_targets(self, day_id):
        return load_scheduled_workout_targets(self.engine, day_id)

    def load_plan_session_links(self):
        return load_plan_session_links(self.engine)

    def assign_scheduled_session(self, day_id, scheduled_date, session_id):
        return assign_scheduled_session(self.engine, day_id, scheduled_date, session_id)

    def unassign_scheduled_session(self, day_id, scheduled_date, session_id):
        return unassign_scheduled_session(self.engine, day_id, scheduled_date, session_id)

    def save_training_plan(self, draft: TrainingPlanDraft, *, plan_id: int | None = None) -> TrainingPlanVersion:
        return save_training_plan(self.engine, draft, plan_id=plan_id)

    def training_plan_storage_ready(self) -> bool:
        return training_plan_storage_ready(self.engine)

    def load_training_plans(self) -> list[TrainingPlanVersion]:
        return load_training_plans(self.engine)

    def load_training_plan_versions(self, plan_id: int) -> list[TrainingPlanVersion]:
        return load_training_plan_versions(self.engine, plan_id)

    def load_training_plan_version(self, version_id: int) -> TrainingPlanVersion | None:
        return load_training_plan_version(self.engine, version_id)

    def load_effective_training_plan(self, plan_id: int, on_date: date) -> TrainingPlanVersion | None:
        return load_effective_training_plan(self.engine, plan_id, on_date)

    def load_exercises(self) -> pd.DataFrame:
        """Load all exercises from the database."""
        return get_exercises(self.engine)

    def load_exercise_muscle_targets(self) -> pd.DataFrame:
        """Load detailed exercise-to-muscle mappings if the mapping table exists."""
        query = text(
            """
            SELECT exercise_id, muscle_group, muscle_name, role, set_factor
            FROM exercise_muscle_map
            ORDER BY exercise_id, muscle_group, muscle_name
            """
        )
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(query, conn)
        except Exception:
            logger.exception("load_exercise_muscle_targets failed")
            return pd.DataFrame(
                columns=["exercise_id", "muscle_group", "muscle_name", "role", "set_factor"]
            )

    def load_sets_ui(self) -> pd.DataFrame:
        """Sets prepared for UI (joins, names, volume)."""
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

    def add_exercise(
        self,
        name: str,
        category: str | None = None,
        body_part: str | None = None,
    ) -> bool:
        """Insert a new exercise into the database.

        Returns True on success, False on database error.
        """
        try:
            return insert_exercise(self.engine, name, category, body_part)
        except Exception as e:
            logger.exception("add_exercise failed: %s", e)
            return False

    def add_full_session(
        self,
        session_date: Any,
        notes: str,
        exercise_name: str,
        sets_data: List[Dict[str, Any]],
        session_start: time,
        session_end: time,
    ) -> bool:
        """Insert a complete workout session including exercise and sets.

        Returns True on success or re-raises the exception if the operation fails.
        """
        try:
            engine = self.engine
            with engine.begin() as conn:
                qry = text(
                    "SELECT session_id FROM workout_sessions WHERE CAST(session_date AS DATE) = :session_date"
                )
                row = conn.execute(qry, {"session_date": session_date}).fetchone()
                if row:
                    session_id = row[0]
                else:
                    insert_q = text(
                        """INSERT INTO workout_sessions (session_date, notes, start_time, end_time)
                           VALUES (:date, :notes, :start_time, :end_time)
                           RETURNING session_id"""
                    )
                    session_id = conn.execute(
                        insert_q,
                        {
                            "date": session_date,
                            "notes": notes,
                            "start_time": session_start,
                            "end_time": session_end,
                        },
                    ).scalar()

                ex_id_q = text(
                    "SELECT exercise_id FROM Exercises WHERE exercise_name = :name"
                )
                res = conn.execute(ex_id_q, {"name": exercise_name}).fetchone()
                if not res:
                    raise ValueError("Exercise not found")
                exercise_id = res[0]

                insert_we = text(
                    "INSERT INTO workout_exercises (session_id, exercise_id) VALUES (:sid, :eid) RETURNING workout_exercise_id;")
                workout_ex_id = conn.execute(
                    insert_we, {"sid": session_id, "eid": exercise_id}
                ).scalar()

                for idx, s in enumerate(sets_data, start=1):
                    ins_set = text(
                        """
                        INSERT INTO workout_sets
                            (workout_exercise_id, set_number, repetitions, weight, duration_seconds, RIR)
                        VALUES
                            (:weid, :num, :reps, :weight, :duration_seconds, :rir)
                        RETURNING set_id
                        """
                    )
                    result = conn.execute(
                        ins_set,
                        {
                            "weid": workout_ex_id,
                            "num": idx,
                            "reps": s["reps"],
                            "weight": s["weight"],
                            "duration_seconds": s.get("duration_seconds"),
                            "rir": s["rir"],
                        },
                    )
                    set_id = result.scalar_one()
                    if s.get("is_warmup") is not None:
                        if type(s["is_warmup"]) is not bool:
                            raise ValueError("Invalid set classification")
                        conn.execute(classifications.insert().values(set_id=set_id, is_warmup=s["is_warmup"]))
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

    def load_sets_raw(self) -> pd.DataFrame:
        """Raw workout sets for metrics (IDs only)."""
        return get_sets_raw(self.engine)

    def load_workout_exercises(self) -> pd.DataFrame:
        query = text(
            """
            SELECT workout_exercise_id, session_id, exercise_id
            FROM workout_exercises
            """
        )
        with self.engine.connect() as conn:
            return pd.read_sql(query, conn)

    def delete_session(self, session_id: int) -> bool:
        try:
            return delete_workout_session(self.engine, session_id)
        except Exception:
            logger.exception("delete_session failed")
            return False
        
