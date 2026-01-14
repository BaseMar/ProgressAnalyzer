import logging
import pandas as pd
from sqlalchemy import text


def get_workout_sessions(engine) -> pd.DataFrame:
    """Retrieve all workout sessions as a Pandas DataFrame.

    Returns a DataFrame with one row per session including SessionID, SessionDate,
    ExerciseCount and TotalVolume aggregated from sets.
    """
    query = text(
        """
        SELECT ws.SessionID, ws.SessionDate, ws.StartTime, ws.EndTime
        FROM WorkoutSessions ws
        ORDER BY ws.SessionDate DESC;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def get_exercises(engine) -> pd.DataFrame:
    """Retrieve all exercises from the database with their associated body part and category.

    Returns a DataFrame with columns: ExerciseID, ExerciseName, Category, BodyPart.
    """
    query = text(
        """
        SELECT ExerciseID, ExerciseName, Category, BodyPart
        FROM Exercises
        ORDER BY BodyPart, ExerciseName;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def get_all_sets(engine) -> pd.DataFrame:
    """Retrieve detailed information about all workout sets.

    Returns a DataFrame containing set-level information such as SetID, SessionDate,
    ExerciseName, BodyPart, SetNumber, Repetitions, Weight, Volume and RPE.
    """
    query = text(
        """
        SELECT ws2.SetID, ws.SessionDate, e.ExerciseName, e.BodyPart, ws2.SetNumber, 
               ws2.Repetitions, ws2.Weight, (ws2.Repetitions * ws2.Weight) AS Volume, ws2.RIR
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        ORDER BY ws.SessionDate, e.ExerciseName, ws2.SetNumber;
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
        SELECT ws.SessionDate, e.ExerciseName, AVG(ws2.Weight) AS AvgWeight, MAX(ws2.Weight) AS MaxWeight, 
               SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        WHERE e.ExerciseName = :exercise_name
        GROUP BY ws.SessionDate, e.ExerciseName
        ORDER BY ws.SessionDate;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"exercise_name": exercise_name})
    return df


def get_volume_by_bodypart(engine) -> pd.DataFrame:
    """Retrieve training volume aggregated by body part and session date.

    Returns a DataFrame with columns: BodyPart, SessionDate, TotalVolume.
    """
    query = text(
        """
        SELECT e.BodyPart, ws.SessionDate, SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        GROUP BY e.BodyPart, ws.SessionDate
        ORDER BY ws.SessionDate;
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
        SELECT MeasurementDate, Chest, Waist, Abdomen, Hips, Thigh, Calf, Biceps
        FROM BodyMeasurements
        ORDER BY MeasurementDate;
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def get_body_composition(engine) -> pd.DataFrame:
    """Retrieve body composition records from the database.

    Returns a DataFrame ordered by MeasurementDate with columns like Weight,
    MuscleMass, FatMass, WaterMass, BodyFatPercentage and Method.
    """
    query = text(
        """
        SELECT MeasurementDate, Weight, MuscleMass, FatMass, WaterMass, BodyFatPercentage, Method
        FROM BodyComposition
        ORDER BY MeasurementDate;
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
        INSERT INTO Exercises (ExerciseName, Category, BodyPart)
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

    The function inserts a row into the WorkoutExercises table linking a session
    with an exercise and returns the generated WorkoutExerciseID.
    """
    query = text(
        """
        INSERT INTO WorkoutExercises (SessionID, ExerciseID)
        OUTPUT INSERTED.WorkoutExerciseID
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

    Parameters match the WorkoutSets table columns: WorkoutExerciseID, SetNumber,
    Repetitions and Weight.
    """
    query = text(
        """
        INSERT INTO WorkoutSets (WorkoutExerciseID, SetNumber, Repetitions, Weight)
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
    """Return the ExerciseID for the given exercise name, or None if not found."""
    query = text("SELECT ExerciseID FROM Exercises WHERE ExerciseName = :name")
    with engine.connect() as conn:
        result = conn.execute(query, {"name": exercise_name}).fetchone()
        return result[0] if result else None


def insert_body_measurements(engine, data):
    """Insert a body measurements record into the BodyMeasurements table.

    Expects `data` mapping to keys: date, chest, waist, abdomen, hips, thigh,
    calf and biceps.
    """
    query = text(
        """
        INSERT INTO BodyMeasurements 
        (MeasurementDate, Chest, Waist, Abdomen, Hips, Thigh, Calf, Biceps)
        VALUES (:date, :chest, :waist, :abdomen, :hips, :thigh, :calf, :biceps)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, data)


def insert_body_composition(engine, data):
    """Insert a body composition record into the BodyComposition table.

    Expects `data` mapping to keys: date, weight, muscle_mass, fat_mass, water_mass,
    bf_percent and method.
    """
    query = text(
        """
        INSERT INTO BodyComposition 
        (MeasurementDate, Weight, MuscleMass, FatMass, WaterMass, BodyFatPercentage, Method)
        VALUES (:date, :weight, :muscle_mass, :fat_mass, :water_mass, :bf_percent, :method)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, data)


def insert_session(engine, date, notes):
    """Insert a new workout session into the WorkoutSessions table.

    Parameters:
    - date: session date (datetime/date)
    - notes: optional text notes for the session
    """
    query = text(
        """
        INSERT INTO WorkoutSessions (SessionDate, Notes)
        VALUES (:date, :notes)
    """
    )
    with engine.begin() as conn:
        conn.execute(query, {"date": date, "notes": notes})

def get_sets_raw(engine) -> pd.DataFrame:
    query = text(
        """
        SELECT
            ws2.WorkoutExerciseID,
            ws2.SetNumber,
            ws2.Repetitions,
            ws2.Weight,
            ws2.RIR
        FROM WorkoutSets ws2
        ORDER BY ws2.WorkoutExerciseID, ws2.SetNumber
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(query, conn)
