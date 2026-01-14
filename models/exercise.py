from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    exercise_id: int
    name: str
    primary_muscle_group_id: int | None
    body_part: str | None = None