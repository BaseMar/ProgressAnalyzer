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

from dataclasses import dataclass
from datetime import date

@dataclass
class AnalizaSkladuCiala:
    data: date
    waga: float
    masa_miesniowa: float
    masa_tluszczowa: float
    tkanka_tluszczowa: float
    procent_wody: float
    masa_wody: float
    miesnie_tulow: float
    miesnie_l_rece: float
    miesnie_p_rece: float
    miesnie_l_noga: float
    miesnie_p_noga: float
    tluszcz_tulow: float
    tluszcz_l_rece: float
    tluszcz_p_rece: float
    tluszcz_l_noga: float
    tluszcz_p_noga: float
    niechciany_tluszcz: float
    notatka: str
