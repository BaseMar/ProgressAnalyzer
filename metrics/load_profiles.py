"""Deterministic conventions for new entries and explicitly resolved old logs."""

from math import isfinite

from models.load_profile import ExerciseLoadProfile
from models.set_load import SetLoad


def resolve_exercise_load_profile(
    exercise_id, name, *, saved=None, history=(), body_mass_confirmed=False
):
    if saved is not None:
        return saved
    from metrics.load_metrics import suggested_load_type

    if body_mass_confirmed:
        return ExerciseLoadProfile(exercise_id, "bodyweight", "body_mass", "body_mass", "history")
    kinds = set(history)
    kind = next(iter(kinds)) if len(kinds) == 1 else suggested_load_type(name)
    normalized = "".join(char for char in name.casefold() if char.isalnum())
    if not kinds and any(
        term in normalized
        for term in ("plank", "pushup", "podciąg", "podciag", "zwis", "pompki", "deska")
    ):
        kind = "assisted_bodyweight" if "wspomag" in normalized else "bodyweight"
    mode = {
        "external": "external",
        "bodyweight": "additional",
        "assisted_bodyweight": "assistance",
    }[kind]
    return ExerciseLoadProfile(
        exercise_id,
        kind,
        mode,
        "external" if kind == "external" else "unknown",
        "history" if len(kinds) == 1 else "catalog",
    )


def resolve_recorded_load(profile, weight, *, body_mass=None, assistance=None, mode=None):
    """Interpret a declared convention; never choose it from the size of a number."""
    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not isfinite(weight)
        or weight < 0
    ):
        raise ValueError("Enter a non-negative recorded weight")
    mode = profile.input_mode if mode is None else mode
    if mode == "unknown":
        # Zero additional weight is unambiguous for an unassisted bodyweight set.
        if profile.load_type == "bodyweight" and weight == 0:
            mode = "additional"
        else:
            return None
    if mode == "external":
        return SetLoad("external", float(weight))
    if mode == "body_mass":
        return SetLoad("bodyweight", 0.0, float(weight) if weight > 0 else body_mass)
    if mode == "assistance":
        return (
            SetLoad("assisted_bodyweight", 0.0, body_mass, float(weight))
            if weight > 0
            else SetLoad("bodyweight", 0.0, body_mass)
        )
    if mode == "total":
        if body_mass is None or (profile.load_type == "assisted_bodyweight" and assistance is None):
            return None
        weight = float(weight) - body_mass + (assistance or 0.0)
        if weight < 0:
            raise ValueError(
                "Recorded total load is below the available body mass; review its convention"
            )
    if mode not in ("additional", "total"):
        raise ValueError("Unknown recorded kilogram convention")
    support = assistance if profile.load_type == "assisted_bodyweight" else 0.0
    return SetLoad(profile.load_type, float(weight), body_mass, support)
