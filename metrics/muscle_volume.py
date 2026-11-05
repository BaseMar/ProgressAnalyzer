"""Weekly plan allocation and general hypertrophy reference values.

10 sets is the IUSCA (2021) general starting prescription to optimize
hypertrophy: https://doi.org/10.47206/ijsc.v1i1.81
20 is a practical reference for diminishing returns, not a recovery ceiling
(ACSM, 2026): https://doi.org/10.1249/MSS.0000000000003897
These are population-level guides, not muscle-specific MEV/MRV estimates.
"""

from collections import defaultdict


BODY_PART_ORDER = (
    "Chest", "Back", "Lower Back", "Glutes", "Legs", "Shoulders",
    "Biceps", "Triceps", "Forearms", "Abs", "Obliques", "Calves",
)
REFERENCE_MIN = 10.0
REFERENCE_MAX = 20.0


def weekly_plan_sets(draft, input_data):
    """Count every weekly slot using the same saved allocation as logged sets.

    No effort or duration multiplier: one planned set counts once before muscle
    allocation. Missing mappings are returned so the UI can avoid partial targets.
    """
    allocations = defaultdict(list)
    for item in input_data.exercise_muscle_targets:
        if item.muscle_group and item.muscle_group.strip():
            allocations[item.exercise_id].append(
                (item.muscle_group.strip().title(), item.set_factor))
    for item in input_data.exercises:
        if item.exercise_id not in allocations and item.body_part and item.body_part.strip():
            allocations[item.exercise_id].append((item.body_part.strip().title(), 1.0))

    totals = defaultdict(float)
    missing = set()
    for day in draft.days:
        for item in day.exercises:
            if item.exercise_id not in allocations:
                missing.add(item.exercise_id)
            for group, factor in allocations[item.exercise_id]:
                totals[group] += item.set_count * factor
    return dict(totals), missing


def volume_ranges(body_parts, weekly_targets=None):
    """Keep actual plan targets, including zero and values outside the guide."""
    return {
        part: {"Min": REFERENCE_MIN, "Target": weekly_targets.get(part, 0.0)
               if weekly_targets is not None else None, "Max": REFERENCE_MAX}
        for part in body_parts
    }
