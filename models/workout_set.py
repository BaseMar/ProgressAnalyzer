from dataclasses import dataclass

from models.set_load import SetLoad


@dataclass(frozen=True)
class WorkoutSet:
    workout_exercise_id: int
    set_number: int
    repetitions: int
    weight: float
    rir: int | None
    duration_seconds: int | None = None
    is_warmup: bool | None = None
    load: SetLoad | None = None

    def __post_init__(self):
        if self.load is not None and (
            not isinstance(self.load, SetLoad) or self.weight != self.load.external_weight_kg
        ):
            raise ValueError("Set weight must match its explicit external weight")
