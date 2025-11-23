from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class WorkoutSet:
    """
    Represents a single set in a given exercise.

    Attributes:
    ----------
    set_number : int
        Set number (e.g., 1, 2, 3)
    reps : int
        Number of repetitions in the set
    weight : float
        Weight used (0 if bodyweight)
    rpe : Optional[int]
        Subjective intensity of effort (Rate of Perceived Exertion), 1–10
    """

    set_number: int
    reps: int
    weight: float
    rpe: Optional[int] = None


@dataclass
class WorkoutExercise:
    """
    Represents one exercise within a workout session.

    Attributes:
    ----------
    name : str
        Exercise name (e.g., "Incline Dumbbell Press")
    body_part : str
        Main muscle group (e.g., "Chest", "Back")
    sets : List[WorkoutSet]
        List of sets performed for this exercise
    """

    name: str
    body_part: str
    sets: List[WorkoutSet]


@dataclass
class WorkoutSession:
    """
    Represents a complete user workout session.

    Attributes:
    ----------
    session_id : int
        Unique session identifier in the database
    session_date : date
        Date the workout was performed
    exercises : List[WorkoutExercise]
        List of exercises performed during the session
    notes : Optional[str]
        Additional notes about the workout (e.g., how you felt, comments)
    """

    session_id: int
    session_date: date
    exercises: List[WorkoutExercise]
    notes: Optional[str] = None
