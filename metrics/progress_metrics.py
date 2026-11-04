from collections import defaultdict
from datetime import time
from statistics import mean

from metrics.input import MetricsInput
from metrics.utils import is_duration_set, set_duration_seconds, set_estimated_1rm


def compute_progress_metrics(input: MetricsInput) -> dict:
    """Compare early/late windows of up to three non-overlapping sessions.

    Each session contributes its best estimated 1RM (or longest timed set),
    regardless of set order/count. At least two comparable sessions are needed.
    This describes recorded performance; it does not assess technique or RIR.
    """
    if not input.sets or not input.workout_exercises or not input.sessions:
        return {}

    we_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}
    sessions = {s.session_id: s for s in input.sessions}
    we_to_session = {we.workout_exercise_id: we.session_id for we in input.workout_exercises}
    exercise_sets = defaultdict(lambda: defaultdict(list))
    exercise_name_map = {e.exercise_id: e.name for e in input.exercises}

    for s in input.sets:
        ex_id = we_to_exercise.get(s.workout_exercise_id)
        session_id = we_to_session.get(s.workout_exercise_id)
        if ex_id is not None and session_id in sessions:
            exercise_sets[ex_id][session_id].append(s)

    per_exercise = {}
    improving = stagnating = regressing = 0
    progress_values = []

    for ex_id, by_session in exercise_sets.items():
        session_order = sorted(by_session, key=lambda sid: (
            sessions[sid].session_date, sessions[sid].start_time or time.min, sid,
        ))
        one_rms, durations = [], []
        for session_id in session_order:
            sets = by_session[session_id]
            strength_values = [
                value for s in sets
                if (value := set_estimated_1rm(s)) is not None and value > 0
            ]
            duration_values = [set_duration_seconds(s) for s in sets if is_duration_set(s)]
            if strength_values:
                one_rms.append(max(strength_values))
            if duration_values:
                durations.append(max(duration_values))
        values = one_rms if one_rms else durations
        metric_type = "estimated_1rm" if one_rms else "duration_seconds"

        if len(values) < 2:
            continue
        
        n = min(3, len(values)//2)
        start = mean(values[:n])
        end = mean(values[-n:])
        progress_pct = round(((end - start) / start) * 100, 2) if start else 0

        if progress_pct > 2:
            improving += 1
        elif progress_pct < -2:
            regressing += 1
        else:
            stagnating += 1

        progress_values.append(progress_pct)

        row = {
            "exercise_name": exercise_name_map.get(ex_id, f"Exercise {ex_id}"),
            "metric_type": metric_type,
            "progress_pct": progress_pct,
            "exposure_count": len(values),
        }
        if metric_type == "estimated_1rm":
            row["start_1rm"] = round(start, 2)
            row["end_1rm"] = round(end, 2)
        else:
            row["start_duration_seconds"] = round(start, 2)
            row["end_duration_seconds"] = round(end, 2)

        per_exercise[ex_id] = row

    global_metrics = {
        "avg_strength_progress_pct": round(mean(progress_values), 2)
        if progress_values
        else None,
        "improving_exercises": improving,
        "stagnating_exercises": stagnating,
        "regressing_exercises": regressing,
    }

    return {
        "per_exercise": per_exercise,
        "global": global_metrics,
    }
