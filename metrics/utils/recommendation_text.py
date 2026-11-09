"""Shared target formatting for recommendation cards and analytical actions."""


def goal_summary(recommendation):
    """Keep uniform sets compact while preserving unequal per-set targets."""
    goals = recommendation.goals
    if not goals:
        return "Target not available yet"
    quantities = [
        str(item.minimum) if item.minimum == item.maximum else f"{item.minimum}–{item.maximum}"
        for item in goals
    ]
    unit = "reps" if goals[0].unit == "reps" else "s"
    if any(item.weight is None for item in goals):
        label = " · ".join(
            f"S{i}: load selected manually × {quantity} {unit}"
            if item.weight is None
            else f"S{i}: {item.weight:g} kg × {quantity} {unit}"
            for i, (item, quantity) in enumerate(zip(goals, quantities), 1)
        )
        return label + (
            f" · RIR ≥ {recommendation.target_rir}" if recommendation.target_rir is not None else ""
        )
    if any(item.load_type in ("bodyweight", "assisted_bodyweight") for item in goals):
        parts = []
        for index, (item, quantity) in enumerate(zip(goals, quantities), 1):
            setting = f"bodyweight + {item.weight:g} kg"
            if item.load_type == "assisted_bodyweight":
                setting += (
                    f" · assistance {item.assistance_kg:g} kg"
                    if item.assistance_kg is not None
                    else " · assistance unknown"
                )
            parts.append(f"S{index}: {setting} × {quantity} {unit}")
        label = " · ".join(parts)
        if recommendation.target_rir is not None:
            label += f" · RIR ≥ {recommendation.target_rir}"
        return label
    if all(item.weight == goals[0].weight for item in goals):
        quantity = (
            f"{len(goals)} × {quantities[0]}"
            if len(set(quantities)) == 1
            else " / ".join(quantities)
        )
        load = f"{goals[0].weight:g} kg · " if goals[0].weight else ""
        label = f"{load}{quantity} {unit}"
    else:
        label = " · ".join(
            f"S{index}: {item.weight:g} kg × {quantity} {unit}"
            for index, (item, quantity) in enumerate(zip(goals, quantities), start=1)
        )
    if recommendation.target_rir is not None:
        label += (
            f" · RIR {recommendation.target_rir}–{recommendation.target_rir_max}"
            if recommendation.target_rir_max is not None
            else f" · RIR ≥ {recommendation.target_rir}"
        )
    return label
