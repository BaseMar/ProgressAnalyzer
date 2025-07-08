from dataclasses import dataclass
from datetime import date
from typing import List

@dataclass
class Cwiczenie:
    id: int
    nazwa: str
    jednostka: str
    partie_glowne: str
    partie_szczeg: str

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
