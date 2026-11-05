"""Explicit load convention and a body-mass snapshot for one recorded set."""
from dataclasses import dataclass
from math import isfinite


def _valid_mass(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"{label} must be {'positive' if positive else 'non-negative'}")


@dataclass(frozen=True)
class SetLoad:
    """External weight is additional load for bodyweight exercises.

    Missing body mass or unknown assistance leaves total load unknown. Assistance
    is a measured counterweight in kg, not a guessed resistance-band value.
    The total estimates supported system mass, not force in individual muscles.
    """
    load_type: str
    external_weight_kg: float = 0.0
    body_mass_kg: float | None = None
    assistance_kg: float | None = 0.0

    def __post_init__(self):
        if self.load_type not in ("external", "bodyweight", "assisted_bodyweight"):
            raise ValueError("Unsupported load type")
        _valid_mass(self.external_weight_kg, "External weight")
        if self.body_mass_kg is not None:
            _valid_mass(self.body_mass_kg, "Body mass", positive=True)
        if self.assistance_kg is not None:
            _valid_mass(self.assistance_kg, "Assistance")
        if self.load_type == "external" and self.body_mass_kg is not None:
            raise ValueError("External-only load cannot contain body mass")
        if self.load_type != "assisted_bodyweight" and self.assistance_kg != 0:
            raise ValueError("Only assisted bodyweight sets can contain assistance")
        if self.load_type == "assisted_bodyweight" and self.assistance_kg == 0:
            raise ValueError("Assisted sets require positive or unknown assistance")
        total = self.total_load_kg
        if total is not None:
            if not isfinite(total):
                raise ValueError("Total load must be finite")
            if total < 0:
                raise ValueError("Assistance cannot exceed body mass plus external weight")

    @property
    def total_load_kg(self) -> float | None:
        if self.load_type == "external":
            return self.external_weight_kg
        if self.body_mass_kg is None or self.assistance_kg is None:
            return None
        return self.body_mass_kg + self.external_weight_kg - self.assistance_kg
