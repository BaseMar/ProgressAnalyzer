"""Shared target formatting for recommendation cards and analytical actions."""


def goal_summary(recommendation):
    """Keep uniform sets compact while preserving unequal per-set targets."""
    goals = recommendation.goals
    if not goals:
        return "Target not available yet"
    quantities = [str(item.minimum) if item.minimum == item.maximum else f"{item.minimum}–{item.maximum}" for item in goals]
    unit = "reps" if goals[0].unit == "reps" else "s"
    if all(item.weight == goals[0].weight for item in goals):
        quantity = f"{len(goals)} × {quantities[0]}" if len(set(quantities)) == 1 else " / ".join(quantities)
        load = f"{goals[0].weight:g} kg · " if goals[0].weight else ""
        label = f"{load}{quantity} {unit}"
    else:
        label = " · ".join(f"S{index}: {item.weight:g} kg × {quantity} {unit}"
                           for index, (item, quantity) in enumerate(zip(goals, quantities), start=1))
    if recommendation.target_rir is not None:
        label += f" · RIR ≥ {recommendation.target_rir}"
    return label
