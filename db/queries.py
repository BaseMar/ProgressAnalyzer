import logging
import pandas as pd
from sqlalchemy import text


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

def get_exercise_progress(engine, exercise_name: str) -> pd.DataFrame:
    """Compute per-session progress metrics for a single exercise.

    Returns a DataFrame grouped by session date for the given exercise_name with
    AvgWeight, MaxWeight and TotalVolume per session.
    """
    query = text(
        """
        SELECT ws.session_date, e.exercise_name, AVG(ws2.weight) AS Avgweight, MAX(ws2.weight) AS Maxweight, 
               SUM(ws2.repetitions * ws2.weight) AS TotalVolume
        FROM workout_sets ws2
        JOIN workout_exercises we ON ws2.workout_exercise_id = we.workout_exercise_id
        JOIN workout_sessions ws ON we.session_id = ws.session_id
        JOIN exercises e ON we.exercise_id = e.exercise_id
        WHERE e.exercise_name = :exercise_name
        GROUP BY ws.session_date, e.exercise_name
        ORDER BY ws.session_date;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"exercise_name": exercise_name})
    return df

def get_volume_by_bodypart(engine) -> pd.DataFrame:
    """Retrieve training volume aggregated by body part and session date.

    Returns a DataFrame with columns: body_part, session_date, TotalVolume.
    """
    query = text(
        """
        SELECT e.body_part, ws.session_date, SUM(ws2.repetitions * ws2.weight) AS TotalVolume
        FROM workout_sets ws2
        JOIN workout_exercises we ON ws2.workout_exercise_id = we.workout_exercise_id
        JOIN workout_sessions ws ON we.session_id = ws.session_id
        JOIN exercises e ON we.exercise_id = e.exercise_id
        GROUP BY e.body_part, ws.session_date
        ORDER BY ws.session_date;
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

def insert_exercise(engine, name: str, category: str, body_part: str) -> bool:
    """Insert a new exercise into the database.

    Returns True on successful insert, otherwise False.
    """
    query = text(
        """
        INSERT INTO exercises (exercise_name, Category, body_part)
        VALUES (:name, :category, :body_part)
    """
    )
    try:
        with engine.begin() as conn:
            conn.execute(
                query, {"name": name, "category": category, "body_part": body_part}
            )
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("SQL error when adding exercise: %s", e)
        return False

def insert_workout_exercise(engine, session_id: int, exercise_id: int):
    """Insert a workout-exercise relation and return the new record ID.

    The function inserts a row into the workout_exercises table linking a session
    with an exercise and returns the generated workout_exercise_id.
    """
    query = text(
        """
        INSERT INTO workout_exercises (session_id, exercise_id)
        RETURNING workout_exercise_id
        VALUES (:session_id, :exercise_id)
    """
    )
    with engine.begin() as conn:
        result = conn.execute(
            query, {"session_id": session_id, "exercise_id": exercise_id}
        )
        workout_exercise_id = result.scalar()
    return workout_exercise_id

def insert_workout_set(
    engine, workout_exercise_id: int, set_number: int, repetitions: int, weight: float
):
    """Insert a single workout set for a given workout-exercise relation.

    Parameters match the workout_sets table columns: workout_exercise_id, set_number,
    repetitions and Weight.
    """
    query = text(
        """
        INSERT INTO workout_sets (workout_exercise_id, set_number, repetitions, weight)
        VALUES (:workout_exercise_id, :set_number, :reps, :weight)
    """
    )
    with engine.begin() as conn:
        conn.execute(
            query,
            {
                "workout_exercise_id": workout_exercise_id,
                "set_number": set_number,
                "reps": repetitions,
                "weight": weight,
            },
        )

def get_exercise_id_by_name(engine, exercise_name: str) -> int:
    """Return the exercise_id for the given exercise name, or None if not found."""
    query = text("SELECT exercise_id FROM exercises WHERE exercise_name = :name")
    with engine.connect() as conn:
        result = conn.execute(query, {"name": exercise_name}).fetchone()
        return result[0] if result else None

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

def insert_session(engine, date, notes):
    """Insert a new workout session into the workout_sessions table.

    Parameters:
    - date: session date (datetime/date)
    - notes: optional text notes for the session
    """
    query = text(
        """
        INSERT INTO workout_sessions (session_date, notes)
        VALUES (:date, :notes)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, {"date": date, "notes": notes})

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
    except Exception as e:
        logging.getLogger(__name__).error(f"SQL Error: {e}")
        raise e