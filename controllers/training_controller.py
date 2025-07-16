from models.models import Training
from storage.training_storage import save_training, load_training_history

class TrainingController:
    def __init__(self):
        pass

    def save_training(self, training: Training):
        save_training(training)

    def get_training_history(self):
        return load_training_history()