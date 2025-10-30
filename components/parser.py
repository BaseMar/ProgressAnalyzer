import re
import pandas as pd
import pyodbc
import streamlit as st
from db.connection import get_connection

# --- ETAP 1: Analiza pliku (bez zapisu) ---
def preview_training_file(file_content):
    """ Analizuje plik .txt z treningiem i zwraca DataFrame z danymi. 
    Zabezpieczenia:
        - tylko .txt
        - puste pliki / błędy formatowania nie crashują aplikacji
    """
    try:
        content = file_content.read().decode("utf-8").strip()

        if not content:
            st.error("Plik jest pusty lub nie został poprawnie odczytany.")
            return pd.DataFrame()

        current_date = None
        current_exercise = None
        sessions = []

        lines = content.splitlines()
        date_pattern = re.compile(r"\d{2}\.\d{2}\.\d{4}")
        exercise_pattern = re.compile(r"^\d+\.\s*(.+)$")
        series_pattern = re.compile(r"(\d+)x?(\d+)?")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if date_pattern.match(line):
                current_date = re.search(date_pattern, line).group()

            elif exercise_pattern.match(line):
                current_exercise = exercise_pattern.match(line).group(1).strip()

            elif series_pattern.findall(line) and current_exercise:
                series_data = line.split("/")
                for s in series_data:
                    match = series_pattern.match(s.strip())
                    if not match:
                        continue
                    reps = int(match.group(1))
                    weight = match.group(2)
                    weight = float(weight) if weight else None

                    sessions.append({
                        "Data sesji": current_date,
                        "Ćwiczenie": current_exercise,
                        "Powtórzenia": reps,
                        "Ciężar (kg)": weight
                    })

        if not sessions:
            st.warning("Nie znaleziono żadnych poprawnych danych treningowych w pliku.")
            return pd.DataFrame()

        return pd.DataFrame(sessions)

    except UnicodeDecodeError:
        st.error("Nie udało się odczytać pliku — upewnij się, że ma kodowanie UTF-8.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd podczas analizy pliku: {e}")
        return pd.DataFrame()


# --- ETAP 2: Zapis do bazy danych ---
def save_training_to_db(df, test_mode=False):
    """Zapisuje dane z DataFrame do bazy danych lub tylko symuluje zapis w trybie testowym."""
    if df.empty:
        st.warning("Brak danych do zapisania.")
        return

    if test_mode:
        st.info("Tryb testowy aktywny — dane NIE zostaną zapisane do bazy.")
        st.dataframe(df)
        return

    try:
        conn = get_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM Exercises WHERE ExerciseName = ?)
                BEGIN
                    INSERT INTO Exercises (ExerciseName) VALUES (?)
                END
            """, row["Ćwiczenie"], row["Ćwiczenie"])

            cursor.execute("SELECT ExerciseID FROM Exercises WHERE ExerciseName = ?", row["Ćwiczenie"])
            exercise_id = cursor.fetchone()[0]

            cursor.execute("""
                DECLARE @session_id INT;
                SELECT @session_id = SessionID FROM TrainingSessions WHERE SessionDate = ?;
                IF @session_id IS NULL
                BEGIN
                    INSERT INTO TrainingSessions (SessionDate) VALUES (?);
                    SET @session_id = SCOPE_IDENTITY();
                END
                SELECT @session_id;
            """, row["Data sesji"], row["Data sesji"])
            session_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO TrainingSets (SessionID, ExerciseID, Reps, Weight)
                VALUES (?, ?, ?, ?)
            """, session_id, exercise_id, row["Powtórzenia"], row["Ciężar (kg)"])

        conn.commit()
        st.success("Dane zostały pomyślnie zapisane do bazy!")

    except Exception as e:
        st.error(f"Błąd podczas zapisu danych: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()