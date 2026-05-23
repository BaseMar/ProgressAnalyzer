from collections import defaultdict
from statistics import mean

from metrics.input import MetricsInput
from metrics.utils import set_duration_seconds, set_intensity, set_volume


def compute_fatigue_metrics(input: MetricsInput) -> dict:
    """
    Compute fatigue-related metrics based on training data.

    Fatigue is inferred from:
    - Average RIR
    - Ratio of sets taken to failure
    - Volume load
    - Intensity load

    Returns per-session fatigue indicators and global fatigue trends.
    """

    if not input.sessions or not input.sets:
        return {}

    we_to_session = {
        we.workout_exercise_id: we.session_id
        for we in input.workout_exercises
    }

    sets_by_session = defaultdict(list)
    for s in input.sets:
        session_id = we_to_session.get(s.workout_exercise_id)
        if session_id is not None:
            sets_by_session[session_id].append(s)

    per_session = {}

    fatigue_scores = []
    high_fatigue_flags = []

    for session in input.sessions:
        sets = sets_by_session.get(session.session_id, [])
        if not sets:
            continue

        total_sets = len(sets)
        rir_values = [s.rir for s in sets if s.rir is not None]
        avg_rir = mean(rir_values) if rir_values else None
        sets_to_failure = sum(1 for s in sets if s.rir == 0)
        sets_to_failure_ratio = sets_to_failure / total_sets
        volume_load = sum(set_volume(s) for s in sets)
        duration_load = sum(set_duration_seconds(s) for s in sets)

        intensities = [
            intensity
            for s in sets
            if (intensity := set_intensity(s)) is not None
        ]
        intensity_load = mean(intensities) if intensities else None

        fatigue_score = 0

        if avg_rir is not None:
            fatigue_score += max(0, (3 - avg_rir) / 3) * 0.4

        fatigue_score += sets_to_failure_ratio * 0.3
        fatigue_score += min(volume_load / 10_000, 1) * 0.3
        fatigue_score += min(duration_load / 600, 1) * 0.1
        fatigue_score = round(min(fatigue_score, 1), 3)
        fatigue_scores.append(fatigue_score)
        high_fatigue_flags.append(fatigue_score >= 0.7)

        per_session[session.session_id] = {
            "avg_rir": round(avg_rir, 2) if avg_rir is not None else None,
            "sets_to_failure_ratio": round(sets_to_failure_ratio, 2),
            "volume_load": round(volume_load, 2),
            "duration_load_seconds": duration_load,
            "intensity_load": round(intensity_load, 2) if intensity_load is not None else None,
            "fatigue_score": fatigue_score,
        }

    consecutive_max = 0
    current = 0

    for flag in high_fatigue_flags:
        if flag:
            current += 1
            consecutive_max = max(consecutive_max, current)
        else:
            current = 0

    global_metrics = {
        "avg_fatigue_score": round(mean(fatigue_scores), 3)
        if fatigue_scores
        else None,
        "high_fatigue_sessions_ratio": round(sum(high_fatigue_flags) / len(high_fatigue_flags), 2)
        if high_fatigue_flags
        else None,
        "max_consecutive_high_fatigue_sessions": consecutive_max,
    }

    return {
        "per_session": per_session,
        "global": global_metrics,
    }
