"""Remembered exercise-level conventions; individual set snapshots take priority."""

from dataclasses import dataclass

LOAD_TYPES = ("external", "bodyweight", "assisted_bodyweight")
WEIGHT_MODES = ("external", "additional", "body_mass", "total", "assistance", "unknown")


@dataclass(frozen=True)
class ExerciseLoadProfile:
    exercise_id: int
    load_type: str
    input_mode: str
    legacy_mode: str = "unknown"
    source: str = "catalog"

    def __post_init__(self):
        if type(self.exercise_id) is not int or self.exercise_id < 1:
            raise ValueError("Choose a valid exercise")
        if self.load_type not in LOAD_TYPES or self.source not in ("catalog", "history", "user"):
            raise ValueError("Invalid exercise load profile")
        allowed = {
            "external": ("external",),
            "bodyweight": ("additional", "body_mass", "total"),
            "assisted_bodyweight": ("additional", "total", "assistance"),
        }[self.load_type]
        if self.input_mode not in allowed or self.legacy_mode not in (*allowed, "unknown"):
            raise ValueError("The recorded kilogram convention does not match the exercise type")
