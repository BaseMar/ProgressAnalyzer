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

def insert_workout_exercise(engine, session_id: int, exercise_id: int):
    """Dodaje powiązanie ćwiczenia z sesją i zwraca ID nowego wpisu."""
    query = text("""
        INSERT INTO WorkoutExercises (SessionID, ExerciseID)
        OUTPUT INSERTED.WorkoutExerciseID
        VALUES (:session_id, :exercise_id)
    """)
    with engine.begin() as conn:
        result = conn.execute(query, {"session_id": session_id, "exercise_id": exercise_id})
        workout_exercise_id = result.scalar()
    return workout_exercise_id

def insert_workout_set(engine, workout_exercise_id: int, set_number: int, repetitions: int, weight: float):
    """Dodaje pojedynczą serię ćwiczenia."""
    query = text("""
        INSERT INTO WorkoutSets (WorkoutExerciseID, SetNumber, Repetitions, Weight)
        VALUES (:workout_exercise_id, :set_number, :reps, :weight)
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "workout_exercise_id": workout_exercise_id,
            "set_number": set_number,
            "reps": repetitions,
            "weight": weight
        })

def get_exercise_id_by_name(engine, exercise_name: str) -> int:
    """Zwraca ID ćwiczenia po nazwie."""
    query = text("SELECT ExerciseID FROM Exercises WHERE ExerciseName = :name")
    with engine.connect() as conn:
        result = conn.execute(query, {"name": exercise_name}).fetchone()
        return result[0] if result else None

def insert_body_measurements(engine, data):
    query = text("""
        INSERT INTO BodyMeasurements 
        (MeasurementDate, Chest, Waist, Abdomen, Hips, Thigh, Calf, Biceps)
        VALUES (:date, :chest, :waist, :abdomen, :hips, :thigh, :calf, :biceps)
    """)
    with engine.begin() as conn:
        conn.execute(query, data)

def insert_body_composition(engine, data):
    query = text("""
        INSERT INTO BodyComposition 
        (MeasurementDate, Weight, MuscleMass, FatMass, WaterMass, BodyFatPercentage, Method)
        VALUES (:date, :weight, :muscle_mass, :fat_mass, :water_mass, :bf_percent, :method)
    """)
    with engine.begin() as conn:
        conn.execute(query, data)

def insert_session(engine, date, notes):
    """Dodaje nową sesję treningową do tabeli WorkoutSessions."""
    query = text("""
        INSERT INTO WorkoutSessions (SessionDate, Notes)
        VALUES (:date, :notes)
    """)
    with engine.begin() as conn:
        conn.execute(query, {"date": date, "notes": notes})