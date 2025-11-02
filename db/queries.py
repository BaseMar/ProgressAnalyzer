import pandas as pd
from sqlalchemy import text

def get_workout_sessions(engine) -> pd.DataFrame:
    """Pobiera wszystkie sesje treningowe"""
    query = text("""
        SELECT ws.SessionID, ws.SessionDate, COUNT(DISTINCT we.ExerciseID) AS ExerciseCount, 
               SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSessions ws
        JOIN WorkoutExercises we ON ws.SessionID = we.SessionID
        JOIN WorkoutSets ws2 ON we.WorkoutExerciseID = ws2.WorkoutExerciseID
        GROUP BY ws.SessionID, ws.SessionDate
        ORDER BY ws.SessionDate;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_exercises(engine) -> pd.DataFrame:
    """Pobiera wszystkie ćwiczenia z bazy z przypisaną grupą mięśniową"""
    query = text("""
        SELECT ExerciseID, ExerciseName, Category, BodyPart
        FROM Exercises
        ORDER BY BodyPart, ExerciseName;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_all_sets(engine) -> pd.DataFrame:
    """Pobiera szczegółowe informacje o seriach treningowych"""
    query = text("""
        SELECT ws2.SetID, ws.SessionDate, e.ExerciseName, e.BodyPart, ws2.SetNumber, 
               ws2.Repetitions, ws2.Weight, (ws2.Repetitions * ws2.Weight) AS Volume, ws2.RPE
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        ORDER BY ws.SessionDate, e.ExerciseName, ws2.SetNumber;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_exercise_progress(engine, exercise_name: str) -> pd.DataFrame:
    """Wylicza średnią objętość / intensywność dla danego ćwiczenia"""
    query = text("""
        SELECT ws.SessionDate, e.ExerciseName, AVG(ws2.Weight) AS AvgWeight, MAX(ws2.Weight) AS MaxWeight, 
               SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        WHERE e.ExerciseName = :exercise_name
        GROUP BY ws.SessionDate, e.ExerciseName
        ORDER BY ws.SessionDate;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"exercise_name": exercise_name})
    return df

def get_volume_by_bodypart(engine) -> pd.DataFrame:
    """Pobiera objętość treningową wg. partii mięśniowej"""
    query = text("""
        SELECT e.BodyPart, ws.SessionDate, SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        GROUP BY e.BodyPart, ws.SessionDate
        ORDER BY ws.SessionDate;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_body_measurements(engine) -> pd.DataFrame:
    """Pobiera pomiary ciała z bazy danych"""
    query = text("""
        SELECT MeasurementDate, Chest, Waist, Abdomen, Hips, Thigh, Calf, Biceps
        FROM BodyMeasurements
        ORDER BY MeasurementDate;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def get_body_composition(engine) -> pd.DataFrame:
    """Pobiera skład ciała z bazy danych"""
    query = text("""
        SELECT MeasurementDate, Weight, MuscleMass, FatMass, WaterMass, BodyFatPercentage, Method
        FROM BodyComposition
        ORDER BY MeasurementDate;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

def insert_exercise(engine, name: str, category: str, body_part: str) -> bool:
    """Dodaje nowe ćwiczenie do bazy danych. Zwraca True, jeśli dodano poprawnie."""
    query = text("""
        INSERT INTO Exercises (ExerciseName, Category, BodyPart)
        VALUES (:name, :category, :body_part)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(query, {
                "name": name,
                "category": category,
                "body_part": body_part
            })
        return True
    except Exception as e:
        print(f"Błąd SQL przy dodawaniu ćwiczenia: {e}")
        return False
