from dataclasses import dataclass


@dataclass(frozen=True)
class WorkoutExercise:
    workout_exercise_id: int
    session_id: int
    exercise_id: int
