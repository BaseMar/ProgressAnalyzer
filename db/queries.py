import pandas as pd
from .connection import get_connection

def get_workout_sessions()-> pd.DataFrame:
    """Pobiera wszystkie sesje treningowe"""
    
    conn = get_connection()
    query = """
        SELECT ws.SessionID, ws.SessionDate, COUNT(DISTINCT we.ExerciseID) AS ExerciseCount, 
        SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSessions ws
        JOIN WorkoutExercises we ON ws.SessionID = we.SessionID
        JOIN WorkoutSets ws2 ON we.WorkoutExerciseID = ws2.WorkoutExerciseID
        GROUP BY ws.SessionID, ws.SessionDate
        ORDER BY ws.SessionDate;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_exercises() -> pd.DataFrame:
    """Pobiera wszystkie ćwiczenia z bazy z przypisaną grupą mięśniową"""

    conn = get_connection()
    query = """
        SELECT ExerciseID, ExerciseName, Category, BodyPart
        FROM Exercises
        ORDER BY BodyPart, ExerciseName;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_all_sets()->pd.DataFrame:
    """Pobiera szczegółowe informacje z bazy na temat danego ćwiczenia: 
        dzień, nazwę, grupę mięśniową, il. powt., il. serii, objętość"""
    
    conn = get_connection()
    query = """
        SELECT ws2.SetID, ws.SessionDate, e.ExerciseName, e.BodyPart, ws2.SetNumber, ws2.Repetitions, ws2.Weight,
            (ws2.Repetitions * ws2.Weight) AS Volume, ws2.RPE
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        ORDER BY ws.SessionDate, e.ExerciseName, ws2.SetNumber;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_exercise_progress(exercise_name:str)->pd.DataFrame:
    """Wylicza średnią objętość / intensywność dla danego ćwiczenia"""
    
    conn = get_connection()
    query = """
        SELECT ws.SessionDate, e.ExerciseName, AVG(ws2.Weight) AS AvgWeight, MAX(ws2.Weight) AS MaxWeight, 
        SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        WHERE e.ExerciseName = ?
        GROUP BY ws.SessionDate, e.ExerciseName
        ORDER BY ws.SessionDate;
    """
    df = pd.read_sql(query, conn, params=[exercise_name])
    conn.close()
    return df


def get_volume_by_bodypart()->pd.DataFrame:
    """Pobiera objętośc treningową wg. partii mięśniowej"""

    conn = get_connection()
    query = """
        SELECT e.BodyPart, ws.SessionDate, SUM(ws2.Repetitions * ws2.Weight) AS TotalVolume
        FROM WorkoutSets ws2
        JOIN WorkoutExercises we ON ws2.WorkoutExerciseID = we.WorkoutExerciseID
        JOIN WorkoutSessions ws ON we.SessionID = ws.SessionID
        JOIN Exercises e ON we.ExerciseID = e.ExerciseID
        GROUP BY e.BodyPart, ws.SessionDate
        ORDER BY ws.SessionDate;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_body_measurements()->pd.DataFrame:
    """Pobiera pomiary ciała z bazy danych: klatka/talia/brzuch/biodra/udo/łydki/ramię"""
    
    conn = get_connection()
    query = """
        SELECT MeasurementDate, Chest, Waist, Abdomen, Hips, Thigh, Calf, Biceps
        FROM BodyMeasurements
        ORDER BY MeasurementDate;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def get_body_composition()->pd.DataFrame:
    """Pobiera skład ciała z bazy danych: data pomiaru/waga/masa mięśniowa/masa tłuszczu/masa wody/%tkanki tłuszczowej"""
    
    conn = get_connection()
    query = """
        SELECT MeasurementDate, Weight, MuscleMass, FatMass, WaterMass, BodyFatPercentage, Method
        FROM BodyComposition
        ORDER BY MeasurementDate;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df
