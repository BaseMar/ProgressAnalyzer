from dataclasses import dataclass


@dataclass(frozen=True)
class ExerciseSet:
    session_id: int
    exercise_id: int
    exercise_name: str
    set_number: int
    reps: int
    weight: float
    rir: int | None
