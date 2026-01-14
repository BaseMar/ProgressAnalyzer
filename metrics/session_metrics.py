"""
Session-level training metrics.

This module computes metrics that describe entire workout sessions,
such as duration, volume, intensity, and workload distribution.

All computations are based solely on normalized data provided
via MetricsInput. No database or UI dependencies are allowed here.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, Any

import streamlit

from metrics.input import MetricsInput


def compute_session_metrics(input: MetricsInput) -> Dict[str, Any]:
    """
    Compute session-level training metrics.

    The function returns:
    - per-session metrics (keyed by session_id)
    - global aggregates across all sessions

    Metrics per session:
    - duration_minutes
    - total_sets
    - total_reps
    - total_volume
    - avg_intensity (Epley-based)
    - avg_rir
    - sets_to_failure (RIR == 0)
    - exercises_count

    Global metrics:
    - avg_session_duration
    - avg_volume_per_session
    - avg_sets_per_session
    - avg_sessions_per_week

    Parameters
    ----------
    input : MetricsInput
        Normalized training data loaded from the database.

    Returns
    -------
    dict
        Dictionary with two keys:
        - "per_session": dict[int, dict[str, Any]]
        - "global": dict[str, float | None]
    """

    # Map sessions by ID for fast lookup
    sessions = {s.session_id: s for s in input.sessions}

    # Group sets and exercises per session
    sets_by_session = defaultdict(list)
    exercises_by_session = defaultdict(set)

    # WorkoutExercise -> Session mapping
    workout_exercise_to_session = {we.workout_exercise_id: we.session_id for we in input.workout_exercises}

    # Assign sets to sessions
    for workout_set in input.sets:
        session_id = workout_exercise_to_session.get(workout_set.workout_exercise_id)
        if session_id is None:
            continue
        
        sets_by_session[session_id].append(workout_set)
        exercises_by_session[session_id].add(workout_set.workout_exercise_id)

    per_session: Dict[int, Dict[str, Any]] = {}

    for session_id, sets in sets_by_session.items():
        session = sessions[session_id]

        # Session duration in minutes
        duration_minutes = None
        if session.start_time and session.end_time:
            try:
                start_dt = datetime.combine(session.session_date, session.start_time)
                end_dt = datetime.combine(session.session_date, session.end_time)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                duration_minutes = (end_dt - start_dt).total_seconds() / 60
            except Exception:
                duration_minutes = None

        total_sets = len(sets)
        total_reps = sum(s.repetitions for s in sets)
        total_volume = sum(s.repetitions * s.weight for s in sets)

        # Epley-based intensity estimate
        intensities = [s.weight * (1 + s.repetitions / 30) for s in sets]

        avg_intensity = mean(intensities) if intensities else None
        avg_rir = mean(s.rir for s in sets if s.rir is not None)
        sets_to_failure = sum(1 for s in sets if s.rir == 0)

        per_session[session_id] = {
            "session_date": session.session_date,
            "duration_minutes": duration_minutes,
            "total_sets": total_sets,
            "total_reps": total_reps,
            "total_volume": total_volume,
            "avg_intensity": avg_intensity,
            "avg_rir": avg_rir,
            "sets_to_failure": sets_to_failure,
            "exercises_count": len(exercises_by_session[session_id]),
        }


    # -------- Global aggregates --------
    durations = [s["duration_minutes"] for s in per_session.values() if s["duration_minutes"] is not None]
    volumes = [s["total_volume"] for s in per_session.values()]
    sets_counts = [s["total_sets"] for s in per_session.values()]

    # ISO year-week pairs
    weeks = {session.session_date.isocalendar()[:2] for session in input.sessions}

    global_metrics = {
        "avg_session_duration": mean(durations) if durations else None,
        "avg_volume_per_session": mean(volumes) if volumes else None,
        "avg_sets_per_session": mean(sets_counts) if sets_counts else None,
        "avg_sessions_per_week": (len(input.sessions) / len(weeks) if weeks else None),
        }

    return {
        "per_session": per_session,
        "global": global_metrics,
    }
