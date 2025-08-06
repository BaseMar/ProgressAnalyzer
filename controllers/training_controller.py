from models.models import Training
from storage.training_storage import save_training, load_training_history
import pandas as pd

class TrainingController:
    def __init__(self):
        pass

    def save_training(self, training: Training):
        save_training(training)

    def get_training_history(self):
        return load_training_history()
    
    def map_training_to_muscle_groups(self, training_df: pd.DataFrame, exercise_to_muscle_groups: dict) -> pd.DataFrame:
        """Rozbija treningi na grupy mięśniowe na podstawie przypisania ćwiczeń do partii głównych. Zwraca DataFrame z kolumnami: ['Partia', 'Data', 'Ciezar', 'Powtorzenia']"""
        records = []

        for _, row in training_df.iterrows():
            exercise = row['Cwiczenie']
            date = row['Data']
            weight = row['Ciezar']
            reps = row['Powtorzenia']

            main_muscles = exercise_to_muscle_groups.get(exercise, [])

            for muscle in main_muscles:
                records.append({
                    'Partia': muscle,
                    'Data': date,
                    'Ciezar': weight,
                    'Powtorzenia': reps
                })

        return pd.DataFrame(records)

    def map_exercises_to_muscle_groups(self, exercise_rows):
        grouped = {}
        detailed = {}

        for row in exercise_rows:
            exercise = row.Nazwa
            main_groups = [p.strip().lower() for p in row.PartieGlowne.split(",")]
            detail_groups = [p.strip().lower() for p in row.PartieSzczeg.split(",")]

            grouped[exercise] = main_groups
            detailed[exercise] = detail_groups

        return grouped, detailed