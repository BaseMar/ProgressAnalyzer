from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BodyCompositionEntry:
    date: date
    weight: float
    fat_percentage: float | None
