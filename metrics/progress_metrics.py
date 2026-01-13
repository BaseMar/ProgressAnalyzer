from collections import defaultdict
from statistics import mean

from metrics.input import MetricsInput
from metrics.utils import estimate_1rm


def compute_progress_metrics(input: MetricsInput) -> dict:
    """
    Analyze strength and volume progression per exercise.
    """

    if not input.sets:
        return {}

    we_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}
    exercise_sets = defaultdict(list)

    for s in input.sets:
        ex_id = we_to_exercise.get(s.workout_exercise_id)
        if ex_id:
            exercise_sets[ex_id].append(s)

    per_exercise = {}
    improving = stagnating = regressing = 0
    progress_values = []

    for ex_id, sets in exercise_sets.items():
        sets = sorted(sets, key=lambda s: s.set_id)
        one_rms = [estimate_1rm(s.weight, s.repetitions) for s in sets]
        start = one_rms[0]
        end = one_rms[-1]
        progress_pct = ((end - start) / start * 100) if start else 0
        progress_pct = round(progress_pct, 2)

        if progress_pct > 2:
            improving += 1
        elif progress_pct < -2:
            regressing += 1
        else:
            stagnating += 1

        progress_values.append(progress_pct)

        per_exercise[ex_id] = {
            "start_1rm": round(start, 2),
            "end_1rm": round(end, 2),
            "progress_pct": progress_pct,
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
