from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BodyComposition:
    date: date
    weight: float
    fat_percentage: float | None
