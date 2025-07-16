from models.models import Training
from storage.training_storage import save_training, load_training_history

class TrainingController:
    def __init__(self):
        pass

    def save_training(self, training: Training):
        save_training(training)

    def get_training_history(self):
        return load_training_history()
    
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