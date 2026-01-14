from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BodyComposition:
    date: date
    weight: float
    muscle_mass: float | None
    fat_mass: float | None
    water_mass: float | None
    fat_percentage: float | None
    method: str | None


