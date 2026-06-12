from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetSpec:
    muscle_group: str
    muscle_name: str
    role: str
    set_factor: float | None = None


@dataclass(frozen=True)
class SpecificExerciseRule:
    required_tokens: tuple[str, ...]
    category: str
    source_note: str
    targets: tuple[TargetSpec, ...]


SPECIFIC_EXERCISE_RULES: tuple[SpecificExerciseRule, ...] = (
    SpecificExerciseRule(
        required_tokens=("hanging", "leg", "raise"),
        category="Push",
        source_note=(
            "Auto-resolved hanging leg raise pattern: hanging leg raises train trunk "
            "flexion with additional grip, shoulder and scapular stabilization demands."
        ),
        targets=(
            TargetSpec("Abs", "Rectus abdominis, transverse abdominis", "primary"),
            TargetSpec("Obliques", "Internal and external obliques", "secondary"),
            TargetSpec("Forearms", "Grip and wrist flexors", "stabilizer"),
            TargetSpec("Shoulders", "Shoulder stabilizers, scapular control", "stabilizer"),
            TargetSpec("Back", "Latissimus dorsi, scapular depressors", "stabilizer"),
        ),
    ),
)
