"""Session comparisons within one known load convention and exercise variant."""
from collections import defaultdict
from datetime import time
from statistics import mean

from metrics.input import MetricsInput
from metrics.load_metrics import load_type, total_load_kg
from metrics.utils.set_values import analysis_sets, is_duration_set, set_duration_seconds, set_estimated_1rm, set_reps


def compute_progress_metrics(input: MetricsInput) -> dict:
    if not input.sets or not input.workout_exercises or not input.sessions:
        return {}
    exercises = {item.workout_exercise_id: item.exercise_id for item in input.workout_exercises}
    workout_sessions = {item.workout_exercise_id: item.session_id for item in input.workout_exercises}
    sessions = {item.session_id: item for item in input.sessions}
    names = {item.exercise_id: item.name for item in input.exercises}
    profiles = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    latest_profiles = defaultdict(lambda: defaultdict(set))
    for item in analysis_sets(input.sets, progression=True, deload_exercise_ids=input.deload_exercise_ids):
        exercise_id = exercises.get(item.workout_exercise_id)
        sid = workout_sessions.get(item.workout_exercise_id)
        if exercise_id is None or sid not in sessions:
            continue
        kind, load = load_type(item), total_load_kg(item)
        timed = is_duration_set(item)
        metric = "duration_seconds" if timed else "repetitions" if kind in ("bodyweight", "assisted_bodyweight") else "estimated_1rm"
        profile = (kind, metric, load if metric != "estimated_1rm" else None)
        latest_profiles[exercise_id][sid].add(profile)
        if load is None:
            continue
        value = set_duration_seconds(item) if timed else set_reps(item) if metric == "repetitions" else set_estimated_1rm(item)
        if value is not None and value > 0:
            profiles[exercise_id][profile][sid].append(value)
    per_exercise = {}
    improving = stagnating = regressing = 0
    strength_values = []
    for exercise_id, session_profiles in latest_profiles.items():
        order = lambda sid: (sessions[sid].session_date, sessions[sid].start_time or time.min, sid)
        latest = max(session_profiles, key=order)
        # A mixed latest execution or unknown current load cannot fall back to an
        # older successful profile and masquerade as current progress.
        if len(session_profiles[latest]) != 1:
            continue
        profile = next(iter(session_profiles[latest]))
        by_session = profiles[exercise_id][profile]
        if latest not in by_session:
            continue
        current_convention = set()
        for sid in sorted(session_profiles, key=order, reverse=True):
            if any(candidate[:2] != profile[:2] for candidate in session_profiles[sid]):
                break
            current_convention.add(sid)
        values = [max(by_session[sid]) for sid in sorted(by_session, key=order) if sid in current_convention]
        if len(values) < 2:
            continue
        n = min(3, len(values) // 2)
        start, end = mean(values[:n]), mean(values[-n:])
        pct = round((end - start) / start * 100, 2)
        improving += pct > 2
        regressing += pct < -2
        stagnating += -2 <= pct <= 2
        kind, metric, load = profile
        if metric == "estimated_1rm":
            strength_values.append(pct)
        field = "1rm" if metric == "estimated_1rm" else "duration_seconds" if metric == "duration_seconds" else "reps"
        per_exercise[exercise_id] = {
            "exercise_name": names.get(exercise_id, f"Exercise {exercise_id}"),
            "metric_type": metric, "progress_pct": pct, "exposure_count": len(values),
            "load_type": kind, "comparison_load_kg": load,
            f"start_{field}": round(start, 2), f"end_{field}": round(end, 2),
        }
    return {"per_exercise": per_exercise, "global": {
        "avg_strength_progress_pct": round(mean(strength_values), 2) if strength_values else None,
        "improving_exercises": improving, "stagnating_exercises": stagnating, "regressing_exercises": regressing,
    }}
