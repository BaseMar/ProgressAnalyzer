"""
Mapping from body_part values (as stored in the DB) to display labels and CSS classes.

To add a new muscle group: just add an entry to BODY_PART_TAGS.
Keys are normalised to lowercase before lookup, so DB casing doesn't matter.
"""

from __future__ import annotations

BODY_PART_TAGS: dict[str, tuple[str, str]] = {
    "legs":       ("Legs",      "legs"),
    "calves":     ("Calves",    "calves"),
    "back":       ("Back",      "back"),
    "chest":      ("Chest",     "chest"),
    "shoulders":  ("Shoulders", "shoulders"),
    "biceps":     ("Biceps",    "biceps"),
    "triceps":    ("Triceps",   "triceps"),
    "core":       ("Core",      "core"),
    "glutes":     ("Glutes",    "glutes"),
}

FALLBACK_TAG: tuple[str, str] = ("Other", "other")


def resolve_muscle_tag(body_part: str | None) -> tuple[str, str]:
    """
    Return (display_label, css_class) for a given body_part string.

    Falls back to ("Other", "other") if the value is missing or unknown.
    Normalises to lowercase before lookup so DB casing doesn't matter.
    """
    if not body_part:
        return FALLBACK_TAG
    return BODY_PART_TAGS.get(body_part.strip().lower(), FALLBACK_TAG)