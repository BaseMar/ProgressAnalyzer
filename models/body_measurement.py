from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class BodyMeasurement:
    date: date
    measurement_type: str
    value: float
