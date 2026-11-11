"""Editable phone notes: proposed targets are separate from performed results."""

from metrics.utils.recommendation_text import goal_summary


def workout_template(upcoming, recommendation, exercise_names):
    lines = [
        f"Date: {upcoming.slot.scheduled_date:%Y-%m-%d}",
        f"Workout: {upcoming.slot.name}",
        "Time:",
        "",
    ]
    targets = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    for index, item in enumerate(recommendation.exercises, 1):
        planned = targets[item.plan_exercise_id]
        name = " ".join(
            exercise_names.get(
                item.actual_exercise_id, f"Exercise #{item.actual_exercise_id}"
            ).split()
        )
        lines.append(f"{index}. {name}")
        if item.goals:
            prefix = "Starting loads; " if item.reason_code == "reuse_exercise_baseline" else ""
            lines.append("Target: " + prefix + goal_summary(item))
        else:
            unit = "s" if planned.target_unit == "seconds" else "reps"
            reserve = str(item.target_rir) if item.target_rir is not None else "unknown"
            lines.append(
                f"Target: {planned.set_count} sets, {planned.target_min}–{planned.target_max} {unit}; "
                f"RIR: {reserve}; load to be selected"
            )
        lines.append("Result:")
        lines.append("RIR:")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
