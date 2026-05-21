import logging
import pandas as pd
from sqlalchemy import text

from db.exercise_muscle_resolver import MuscleTarget, resolve_exercise


def get_workout_sessions(engine) -> pd.DataFrame:
    query = text("""
        SELECT ws.session_id, ws.session_date, ws.start_time, ws.end_time
        FROM workout_sessions ws
        ORDER BY ws.session_date DESC;
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    df["session_date"] = pd.to_datetime(df["session_date"])
    return df

def get_exercises(engine) -> pd.DataFrame:
    """Retrieve all exercises from the database with their associated body part and category.

    Returns a DataFrame with columns: exercise_id, exercise_name, Category, BodyPart.
    """
    query = text(
        """
        SELECT exercise_id, exercise_name, Category, body_part
        FROM exercises
        ORDER BY body_part, exercise_name;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_all_sets(engine) -> pd.DataFrame:
    """Retrieve detailed information about all workout sets."""
    query = text(
        """
        SELECT 
            ws.session_id,
            ws2.set_id, 
            ws.session_date, 
            e.exercise_name, 
            e.body_part, 
            ws2.set_number, 
            ws2.repetitions, 
            ws2.weight, 
            (ws2.repetitions * ws2.weight) AS volume, 
            ws2.rir
        FROM workout_sets ws2
        JOIN workout_exercises we 
            ON ws2.workout_exercise_id = we.workout_exercise_id
        JOIN workout_sessions ws 
            ON we.session_id = ws.session_id
        JOIN exercises e 
            ON we.exercise_id = e.exercise_id
        ORDER BY ws.session_date DESC, e.exercise_name, ws2.set_number;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_body_measurements(engine) -> pd.DataFrame:
    """Retrieve body measurements records from the database.

    Returns a DataFrame ordered by MeasurementDate containing measurement columns
    such as Chest, Waist, Abdomen, Hips, Thigh, Calf and Biceps.
    """
    query = text(
        """
        SELECT measurement_date, chest, waist, abdomen, hips, thigh, calf, biceps
        FROM body_measurements
        ORDER BY measurement_date;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_body_composition(engine) -> pd.DataFrame:
    """Retrieve body composition records from the database.

    Returns a DataFrame ordered by measurement_date with columns like Weight,
    MuscleMass, fat_mass, WaterMass, body_fat_percentage and Method.
    """
    query = text(
        """
        SELECT measurement_date, weight, muscle_mass, fat_mass, water_mass, body_fat_percentage, method
        FROM body_composition
        ORDER BY measurement_date;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def insert_exercise(
    engine,
    name: str,
    category: str | None = None,
    body_part: str | None = None,
    muscle_targets: list[MuscleTarget] | None = None,
) -> bool:
    """Insert a new exercise into the database.

    Returns True on successful insert, otherwise False.
    """
    resolution = resolve_exercise(name, allow_web=True)
    if muscle_targets is None:
        if resolution is None:
            raise ValueError(f"Could not resolve muscle targets for exercise: {name}")
        muscle_targets = resolution.targets
    if category is None:
        category = resolution.category if resolution else "Pull"
    if body_part is None:
        body_part = resolution.body_part if resolution else muscle_targets[0].muscle_group

    exercise_query = text(
        """
        INSERT INTO exercises (exercise_id, exercise_name, category, body_part)
        VALUES (
            (SELECT COALESCE(MAX(exercise_id), 0) + 1 FROM exercises),
            :name,
            :category,
            :body_part
        )
        RETURNING exercise_id
    """
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("LOCK TABLE exercises IN EXCLUSIVE MODE"))
            exercise_id = conn.execute(
                exercise_query,
                {"name": name, "category": category, "body_part": body_part},
            ).scalar()
            upsert_exercise_muscle_targets(conn, exercise_id, muscle_targets)
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("SQL error when adding exercise: %s", e)
        return False


def upsert_exercise_muscle_targets(conn, exercise_id: int, muscle_targets: list[MuscleTarget]) -> None:
    if not muscle_targets:
        return

    muscle_query = text(
        """
        INSERT INTO exercise_muscle_map (
            exercise_id,
            muscle_group,
            muscle_name,
            role,
            set_factor,
            source_note
        )
        VALUES (
            :exercise_id,
            :muscle_group,
            :muscle_name,
            :role,
            :set_factor,
            :source_note
        )
        ON CONFLICT (exercise_id, muscle_group) DO UPDATE
        SET
            muscle_name = EXCLUDED.muscle_name,
            role = EXCLUDED.role,
            set_factor = EXCLUDED.set_factor,
            source_note = EXCLUDED.source_note,
            updated_at = now()
    """
    )
    conn.execute(
        muscle_query,
        [
            {
                "exercise_id": exercise_id,
                "muscle_group": target.muscle_group,
                "muscle_name": target.muscle_name,
                "role": target.role,
                "set_factor": target.set_factor,
                "source_note": target.source_note,
            }
            for target in muscle_targets
        ],
    )

def insert_body_measurements(engine, data):
    """Insert a body measurements record into the body_measurements table.

    Expects `data` mapping to keys: date, chest, waist, abdomen, hips, thigh,
    calf and biceps.
    """
    query = text(
        """
        INSERT INTO body_measurements (measurement_date, chest, waist, abdomen, hips, thigh, calf, biceps)
        VALUES (:date, :chest, :waist, :abdomen, :hips, :thigh, :calf, :biceps)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, data)

def insert_body_composition(engine, data):
    """Insert a body composition record into the body_composition table.

    Expects `data` mapping to keys: date, weight, muscle_mass, fat_mass, water_mass,
    bf_percent and method.
    """
    query = text(
        """
        INSERT INTO body_composition 
        (measurement_date, weight, muscle_mass, fat_mass, water_mass, body_fat_percentage, method)
        VALUES (:date, :weight, :muscle_mass, :fat_mass, :water_mass, :bf_percent, :method)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, data)

def get_sets_raw(engine) -> pd.DataFrame:
    query = text(
        """
        SELECT
            ws2.workout_exercise_id,
            ws2.set_number,
            ws2.repetitions,
            ws2.weight,
            ws2.rir
        FROM workout_sets ws2
        ORDER BY ws2.workout_exercise_id, ws2.set_number
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def delete_workout_session(engine, session_id):
    """Delete session with exercises and series"""
    safe_session_id = int(session_id) 

    query = text("""
        DELETE FROM workout_sets 
        WHERE workout_exercise_id IN (
            SELECT workout_exercise_id FROM workout_exercises WHERE session_id = :sid
        );
        DELETE FROM workout_exercises WHERE session_id = :sid;
        DELETE FROM workout_sessions WHERE session_id = :sid;
    """)

    try:
        with engine.begin() as conn:
            conn.execute(query, {"sid": safe_session_id})
        return True
    except Exception:
        logging.getLogger(__name__).exception("SQL error deleting session")
        raise
