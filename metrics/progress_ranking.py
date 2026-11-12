"""Restore early/late windows using the existing exercise metric series.

Strength estimates and timed holds remain separate. Existing load-convention
and timed-load comparability guards apply before a trend enters the ranking.
No source reads, recommendations or underlying metric calculations change.
"""

from math import isfinite
from statistics import mean

from metrics.utils.dates import to_date
from models.progress_ranking import ExerciseTrend, ProgressRanking


def rank_exercise_progress(exercise_metrics):
    trends, unavailable = [], []
    for exercise_id, item in sorted(exercise_metrics.get("per_exercise", {}).items()):
        available = False
        for measure, series_key, value_key, guard in (
            ("Estimated strength", "per_session_1rm", "estimated_1rm", "strength_trend_1rm"),
            (
                "Hold time",
                "per_session_best_duration",
                "duration_seconds",
                "duration_trend_seconds",
            ),
        ):
            points = item.get(series_key, [])
            if item.get(guard) is None or len(points) < 2:
                continue
            values = [point[value_key] for point in points]
            if any(value is None or not isfinite(value) or value <= 0 for value in values):
                continue
            window = min(3, len(points) // 2)
            baseline, current = mean(values[:window]), mean(values[-window:])
            trends.append(
                ExerciseTrend(
                    exercise_id,
                    item["exercise_name"],
                    measure,
                    baseline,
                    current,
                    round((current / baseline - 1) * 100, 2),
                    len(points),
                    window,
                    tuple(to_date(point["date"]) for point in points[:window]),
                    tuple(to_date(point["date"]) for point in points[-window:]),
                )
            )
            available = True
        if not available:
            unavailable.append(exercise_id)
    return ProgressRanking(tuple(trends), tuple(unavailable))


def ranking_groups(trends):
    """Up to five increases and five lowest non-positive changes; never pad."""
    top = sorted(
        (item for item in trends if item.change_pct > 0),
        key=lambda item: (-item.change_pct, item.name.casefold(), item.exercise_id),
    )[:5]
    bottom = sorted(
        (item for item in trends if item.change_pct <= 0),
        key=lambda item: (item.change_pct, item.name.casefold(), item.exercise_id),
    )[:5]
    return tuple(top), tuple(bottom)
