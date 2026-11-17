"""Readable set targets for workout cards; preserve order and load conventions."""

from html import escape


def _quantity(goal):
    value = str(goal.minimum) if goal.minimum == goal.maximum else f"{goal.minimum}–{goal.maximum}"
    return f"{value} {'s' if goal.unit == 'seconds' else 'reps'}"


def _load(goal):
    if goal.load_type == "manual_bodyweight":
        return "choose added weight or assistance"
    value = f"{goal.weight:g} kg" if goal.weight is not None else "choose load"
    if goal.load_type in ("bodyweight", "assisted_bodyweight"):
        value = "bodyweight + " + value
        if goal.load_type == "assisted_bodyweight":
            assistance = (
                f"{goal.assistance_kg:g} kg" if goal.assistance_kg is not None else "unknown"
            )
            value += f" · assistance {assistance}"
    return value


def recommendation_sets_html(item):
    """Collapse identical sets; show different targets in numbered rows."""
    if not item.goals:
        return ""
    first = item.goals[0]
    if all(goal == first for goal in item.goals):
        content = (
            '<div class="recommendation-goal">'
            f"{len(item.goals)} × {escape(_quantity(first))} · {escape(_load(first))}</div>"
        )
    else:
        rows = "".join(
            '<div class="recommendation-set-row">'
            f'<span class="recommendation-set-label">Set {index}</span>'
            f'<span class="recommendation-set-quantity">{escape(_quantity(goal))}</span>'
            f'<span class="recommendation-set-load">{escape(_load(goal))}</span></div>'
            for index, goal in enumerate(item.goals, 1)
        )
        content = f'<div class="recommendation-set-list">{rows}</div>'
    if item.target_rir is not None:
        reserve = (
            f"RIR {item.target_rir}–{item.target_rir_max}"
            if item.target_rir_max is not None
            else f"RIR ≥ {item.target_rir}"
        )
        content += f'<div class="recommendation-set-rir">{escape(reserve)}</div>'
    return content
