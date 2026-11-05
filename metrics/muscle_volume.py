"""Direct/indirect allocation and current-plan weekly reference totals."""

from collections import defaultdict


BODY_PART_ORDER = (
    "Chest", "Back", "Lower Back", "Glutes", "Legs", "Shoulders",
    "Biceps", "Triceps", "Forearms", "Abs", "Obliques", "Calves",
)

def allocation_components(count, target):
    """Raw role counts and saved weighted contribution; no role guessed from factor."""
    role = target.get("role")
    return {"Direct_Sets": float(count) if role == "primary" else 0.0,
            "Indirect_Sets": float(count) if role in ("secondary", "stabilizer") else 0.0,
            "Stabilizer_Sets": float(count) if role == "stabilizer" else 0.0,
            "Unclassified_Sets": float(count) if role not in ("primary", "secondary", "stabilizer") else 0.0,
            "Total_Sets": float(count) * float(target.get("set_factor", 1.0))}


def weekly_plan_allocation(draft, input_data):
    """Count every weekly slot using the same saved allocation as logged sets.

    Dynamic sets count once before muscle allocation. Timed holds stay separate
    from the hypertrophy guide. Missing mappings prevent partial targets.
    """
    allocations = defaultdict(list)
    for item in input_data.exercise_muscle_targets:
        if item.muscle_group and item.muscle_group.strip():
            allocations[item.exercise_id].append(
                {"muscle_group": item.muscle_group.strip().title(), "set_factor": item.set_factor, "role": item.role})
    for item in input_data.exercises:
        if item.exercise_id not in allocations and item.body_part and item.body_part.strip():
            allocations[item.exercise_id].append({"muscle_group": item.body_part.strip().title(), "set_factor": 1.0, "role": "primary"})

    totals = defaultdict(lambda: defaultdict(float))
    missing = set()
    for day in draft.days:
        for item in day.exercises:
            if item.target_unit == "seconds":
                continue
            if item.exercise_id not in allocations:
                missing.add(item.exercise_id)
            for target in allocations.get(item.exercise_id, ()):
                for field, value in allocation_components(item.set_count, target).items():
                    totals[target["muscle_group"]][field] += value
    return {group: dict(values) for group, values in totals.items()}, missing


def weekly_plan_sets(draft, input_data):
    """Weighted weekly target, with the same counting as the recorded allocation."""
    allocation, missing = weekly_plan_allocation(draft, input_data)
    return {group: row["Total_Sets"] for group, row in allocation.items()}, missing
