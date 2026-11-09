"""Persist complete workout entries atomically, independently of the UI facade."""
import logging
from datetime import timedelta

import pandas as pd
from sqlalchemy import text

from db.set_classifications import classifications
from db.set_loads import insert_set_load, set_load_storage_ready
from models.set_load import SetLoad

logger = logging.getLogger(__name__)


def save_workout_session(engine, session_date, notes, exercises_data, session_start=None, session_end=None):
    """Save every exercise and load snapshot atomically, appending to the day."""
    day = pd.Timestamp(session_date).date()
    if pd.isna(day) or not exercises_data or any(not item.get("sets") for item in exercises_data):
        raise ValueError("Choose a workout date and add at least one set per exercise")
    explicit = False
    for exercise in exercises_data:
        for item in exercise["sets"]:
            load = item.get("load")
            if load is not None:
                explicit = True
                if not isinstance(load, SetLoad) or item["weight"] != load.external_weight_kg:
                    raise ValueError("Set weight must match its explicit external weight")
    if explicit and not set_load_storage_ready(engine):
        raise ValueError("Bodyweight load entry needs database setup (migration 006_set_loads)")
    try:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT session_id FROM workout_sessions "
                "WHERE session_date >= :day AND session_date < :next_day ORDER BY session_id DESC"),
                {"day": day, "next_day": day + timedelta(days=1)}).first()
            if row:
                session_id = row[0]
            else:
                session_id = conn.execute(text("""
                    INSERT INTO workout_sessions (session_date, notes, start_time, end_time)
                    VALUES (:date, :notes, :start_time, :end_time) RETURNING session_id
                """), {"date": day, "notes": notes, "start_time": session_start, "end_time": session_end}).scalar_one()
            for exercise in exercises_data:
                if exercise.get("exercise_id") is not None:
                    res = conn.execute(text("SELECT exercise_id FROM exercises WHERE exercise_id=:id"),
                                       {"id": exercise["exercise_id"]}).fetchone()
                else:
                    res = conn.execute(text("SELECT exercise_id FROM exercises WHERE exercise_name=:name"),
                                       {"name": exercise["name"]}).fetchone()
                if not res:
                    raise ValueError("Exercise not found")
                exercise_id = res[0]

                insert_we = text(
                    "INSERT INTO workout_exercises (session_id, exercise_id) VALUES (:sid, :eid) RETURNING workout_exercise_id;")
                workout_ex_id = conn.execute(
                    insert_we, {"sid": session_id, "eid": exercise_id}
                ).scalar()

                for idx, s in enumerate(exercise["sets"], start=1):
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
                    if s.get("load") is not None:
                        insert_set_load(conn, set_id, s["load"])
                    if s.get("is_warmup") is not None:
                        if type(s["is_warmup"]) is not bool:
                            raise ValueError("Invalid set classification")
                        conn.execute(classifications.insert().values(set_id=set_id, is_warmup=s["is_warmup"]))
        return True
    except Exception:
        logger.exception("add_workout_session failed")
        raise
