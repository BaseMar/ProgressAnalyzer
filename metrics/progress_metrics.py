from collections import defaultdict
from statistics import mean
from typing import Dict

from metrics.input import MetricsInput
from metrics.utils.strength import estimate_1rm


def compute_progress_metrics(input: MetricsInput) -> Dict[str, dict]:
    """
    Analyze strength progression per exercise based on estimated 1RM.

    Progress is calculated by comparing the first and last training session
    for each exercise, using the maximum estimated 1RM per session.
    """

    if not input.sets or not input.workout_exercises or not input.sessions:
        return {}

    # --- mappings ---
    we_to_exercise = {we.workout_exercise_id: we.exercise_id for we in input.workout_exercises}
    session_dates = {s.session_id: s.session_date for s in input.sessions}

    # exercise_id -> date -> list[1RM]
    exercise_session_1rms = defaultdict(lambda: defaultdict(list))

    for s in input.sets:
        ex_id = we_to_exercise.get(s.workout_exercise_id)
        if not ex_id:
            continue

        if s.weight <= 0 or s.repetitions <= 0:
            continue

        est_1rm = estimate_1rm(s.weight, s.repetitions)
        if est_1rm is None:
            continue

        session_id = next(
            (we.session_id for we in input.workout_exercises
             if we.workout_exercise_id == s.workout_exercise_id),
            None,
        )

        session_date = session_dates.get(session_id)
        if not session_date:
            continue

        exercise_session_1rms[ex_id][session_date].append(est_1rm)

    per_exercise = {}
    progress_values = []

    improving = stagnating = regressing = 0

    for ex_id, sessions in exercise_session_1rms.items():
        if len(sessions) < 2:
            continue

        timeline = sorted((date, max(rms)) for date, rms in sessions.items())

        start_1rm = timeline[0][1]
        end_1rm = timeline[-1][1]

        progress_pct = round(((end_1rm - start_1rm) / start_1rm) * 100, 2) if start_1rm else None

        if progress_pct is not None:
            progress_values.append(progress_pct)

            if progress_pct > 2:
                improving += 1
            elif progress_pct < -2:
                regressing += 1
            else:
                stagnating += 1

        per_exercise[ex_id] = {
            "start_1rm": round(start_1rm, 2),
            "end_1rm": round(end_1rm, 2),
            "progress_pct": progress_pct,
        }

    global_metrics = {
        "avg_strength_progress_pct": (
            round(mean(progress_values), 2)
            if progress_values
            else None
        ),
        "improving_exercises": improving,
        "stagnating_exercises": stagnating,
        "regressing_exercises": regressing,
    }

    return {
        "per_exercise": per_exercise,
        "global": global_metrics,
    }
