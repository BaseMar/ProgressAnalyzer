from dataclasses import dataclass


@dataclass(frozen=True)
class WorkoutSet:
    workout_exercise_id: int
    session_id: int
    set_number: int
    repetitions: int
    weight: float
    rir: int | None
