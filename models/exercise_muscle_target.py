from dataclasses import dataclass


@dataclass(frozen=True)
class ExerciseMuscleTarget:
    exercise_id: int
    muscle_group: str
    muscle_name: str
    role: str
    set_factor: float
