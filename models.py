from dataclasses import dataclass
from datetime import date
from typing import List

class Cwiczenie:
    def __init__(self, id, nazwa, jednostka, partie_glowne, partie_szczeg):
        self.id = id
        self.nazwa = nazwa
        self.jednostka = jednostka
        self.partie_glowne = partie_glowne
        self.partie_szczeg = partie_szczeg

    def __str__(self):
        return f"{self.nazwa} ({self.partie_glowne})"
    
@dataclass
class Series:
    powtorzenia: int
    ciezar: float

@dataclass
class TrainingExercise:
    exercise_id: int
    series: List[Series]

@dataclass
class Training:
    data: date
    exercises: List[TrainingExercise]
