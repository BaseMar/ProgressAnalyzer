from collections import defaultdict
from statistics import mean

from metrics.input import MetricsInput


def compute_frequency_metrics(input: MetricsInput) -> dict:
    """
    Compute training frequency metrics.

    Metrics included:
    - Global session frequency (sessions per week, avg days between sessions)
    - Per-exercise session frequency
    - Per-muscle group session frequency

    Frequency is calculated using ISO calendar weeks.
    """

    if not input.sessions:
        return {}

    # ---Helper mappings
    sessions = sorted(input.sessions, key=lambda s: s.session_date)

    workout_exercises_by_session = defaultdict(list)
    for we in input.workout_exercises:
        workout_exercises_by_session[we.session_id].append(we)

    exercise_id_to_name = {e.exercise_id: e.exercise_name for e in input.exercises}
    exercise_id_to_bodypart = {e.exercise_id: e.body_part for e in input.exercises if e.body_part}

    # ---GLOBAL FREQUENCY
    session_dates = [s.session_date for s in sessions]
    iso_weeks = set(d.isocalendar()[:2] for d in session_dates)
    sessions_per_week = len(session_dates) / len(iso_weeks) if iso_weeks else None
    day_gaps = [(session_dates[i] - session_dates[i - 1]).days for i in range(1, len(session_dates))]
    avg_days_between_sessions = mean(day_gaps) if day_gaps else None

    global_metrics = {
        "sessions_per_week": round(sessions_per_week, 2) if sessions_per_week else None,
        "avg_days_between_sessions": round(avg_days_between_sessions, 2)
        if avg_days_between_sessions
        else None,
    }

    # ---PER-EXERCISE FREQUENCY
    exercise_sessions = defaultdict(set)

    for session in sessions:
        for we in workout_exercises_by_session.get(session.session_id, []):
            exercise_sessions[we.exercise_id].add(session.session_date)

    per_exercise = {}

    for exercise_id, dates in exercise_sessions.items():
        dates = sorted(dates)
        weeks = set(d.isocalendar()[:2] for d in dates)

        day_gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]

        per_exercise[exercise_id_to_name.get(exercise_id, str(exercise_id))] = {
            "sessions_per_week": round(len(dates) / len(weeks), 2)
            if weeks
            else None,
            "avg_days_between_sessions": round(mean(day_gaps), 2)
            if day_gaps
            else None,
            "total_sessions": len(dates),
        }

    # ---PER-MUSCLE GROUP FREQUENCY
    muscle_sessions = defaultdict(set)

    for session in sessions:
        for we in workout_exercises_by_session.get(session.session_id, []):
            bodypart = exercise_id_to_bodypart.get(we.exercise_id)
            if bodypart:
                muscle_sessions[bodypart].add(session.session_date)

    per_muscle = {}

    for muscle, dates in muscle_sessions.items():
        weeks = set(d.isocalendar()[:2] for d in dates)

        per_muscle[muscle] = {
            "sessions_per_week": round(len(dates) / len(weeks), 2)
            if weeks
            else None,
            "total_sessions": len(dates),
        }

    return {
        "global": global_metrics,
        "per_exercise": per_exercise,
        "per_muscle_group": per_muscle,
    }
