from collections import defaultdict
from statistics import mean
from metrics.input import MetricsInput
from metrics.utils import estimate_1rm


def compute_progress_metrics(input: MetricsInput) -> dict:
    if not input.sets or not input.workout_exercises or not input.sessions:
        return {}

    we_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}
    session_dates = {s.session_id: s.session_date for s in input.sessions}
    we_to_date = {we.workout_exercise_id: session_dates.get(we.session_id) for we in input.workout_exercises}
    exercise_sets = defaultdict(list)
    exercise_name_map = {e.exercise_id: e.name for e in input.exercises}

    for s in input.sets:
        ex_id = we_to_exercise.get(s.workout_exercise_id)
        date = we_to_date.get(s.workout_exercise_id)
        if ex_id and date:
            exercise_sets[ex_id].append((date, s))

    per_exercise = {}
    improving = stagnating = regressing = 0
    progress_values = []

    for ex_id, entries in exercise_sets.items():
        entries.sort(key=lambda x: x[0])
        one_rms = [estimate_1rm(s.weight, s.repetitions) for _, s in entries]
        if len(one_rms) < 2:
            continue
        
        n = min(3, len(one_rms)//2)
        start = mean(one_rms[:n])
        end = mean(one_rms[-n:])
        progress_pct = round(((end - start) / start) * 100, 2) if start else 0

        if progress_pct > 2:
            improving += 1
        elif progress_pct < -2:
            regressing += 1
        else:
            stagnating += 1

        progress_values.append(progress_pct)

        per_exercise[ex_id] = {
            "exercise_name": exercise_name_map[ex_id],
            "start_1rm": round(start, 2),
            "end_1rm": round(end, 2),
            "progress_pct": progress_pct,
            "exposure_count": len(entries),
        }

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
