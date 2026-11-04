"""Derived set purpose and provenance, independent of stored corrections."""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SetInterpretation:
    kind: Literal["working", "light", "warmup", "low_effort", "unknown", "timed", "deload", "invalid"]
    source: Literal["explicit", "rir", "sequence", "duration", "plan", "unknown", "validation"]
    reason: str
    progression_eligible: bool = False

    @property
    def descriptive(self):
        return self.kind not in ("warmup", "invalid")

    @property
    def counts_for_plan(self):
        return self.kind in ("working", "unknown", "timed", "deload")
