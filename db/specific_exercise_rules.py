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
        required_tokens=("pallof", "press", "rotation"),
        category="Push",
        source_note=(
            "User-provided Pallof press with rotation description: the movement "
            "combines anti-rotation stabilization with controlled trunk rotation, "
            "emphasizing the obliques and deep abdominal musculature while the "
            "spinal, scapular, shoulder and hip musculature stabilizes the body."
        ),
        targets=(
            TargetSpec("Obliques", "Internal and external obliques", "primary"),
            TargetSpec(
                "Abs",
                "Transverse abdominis, rectus abdominis",
                "primary",
            ),
            TargetSpec(
                "Lower Back",
                "Erector spinae, multifidus",
                "stabilizer",
            ),
            TargetSpec(
                "Back",
                "Rhomboids, thoracic and scapular stabilizers",
                "stabilizer",
            ),
            TargetSpec(
                "Shoulders",
                "Rotator cuff and shoulder girdle stabilizers",
                "stabilizer",
            ),
            TargetSpec("Glutes", "Gluteal and hip stabilizers", "stabilizer"),
        ),
    ),
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
