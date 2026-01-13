from dataclasses import dataclass


@dataclass(frozen=True)
class MuscleGroup:
    muscle_group_id: int
    name: str
