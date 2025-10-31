from dataclasses import dataclass
from datetime import date
from typing import List, Optional

@dataclass
class WorkoutSet:
    """
    Reprezentuje pojedynczą serię w danym ćwiczeniu.

    Atrybuty:
    ----------
    set_number : int
        Numer serii (np. 1, 2, 3)
    reps : int
        Liczba powtórzeń w serii
    weight : float
        Użyty ciężar (0 jeśli ciężar ciała)
    rpe : Optional[int]
        Subiektywna intensywność wysiłku (Rate of Perceived Exertion), 1–10
    """
    set_number: int
    reps: int
    weight: float
    rpe: Optional[int] = None

@dataclass
class WorkoutExercise:
    """
    Reprezentuje jedno ćwiczenie w ramach sesji treningowej.

    Atrybuty:
    ----------
    name : str
        Nazwa ćwiczenia (np. "Incline Dumbbell Press")
    body_part : str
        Główna partia mięśniowa (np. "Chest", "Back")
    sets : List[WorkoutSet]
        Lista serii wykonanych dla tego ćwiczenia
    """
    name: str
    body_part: str
    sets: List[WorkoutSet]

@dataclass
class WorkoutSession:
    """
    Reprezentuje całą sesję treningową użytkownika.

    Atrybuty:
    ----------
    session_id : int
        Unikalny identyfikator sesji w bazie danych
    session_date : date
        Data wykonania treningu
    exercises : List[WorkoutExercise]
        Lista ćwiczeń wykonanych podczas sesji
    notes : Optional[str]
        Dodatkowe notatki do treningu (np. samopoczucie, uwagi)
    """
    session_id: int
    session_date: date
    exercises: List[WorkoutExercise]
    notes: Optional[str] = None
