"""Small, interpretable indicators for the plan analysis overview."""

from collections import defaultdict
from datetime import timedelta


def summarize_plan(report, performance):
    eligible = [row for row in report["workouts"] if row["eligible"]]
    weeks = {}
    gaps = defaultdict(int)
    for row in eligible:
        monday = row["scheduled_date"] - timedelta(days=row["scheduled_date"].weekday())
        week = weeks.setdefault(
            monday, dict(week=monday, complete=0, partial=0, unmatched=0, unlinked=0)
        )
        category = (
            "complete"
            if row["complete"]
            else "partial"
            if row["covered_sets"]
            else "unmatched"
            if row["linked"]
            else "unlinked"
        )
        week[category] += 1
        gaps[row["name"]] += row["planned_sets"] - row["covered_sets"]
    eligible_slots = {(row["day_id"], row["scheduled_date"]) for row in eligible}
    observed = [
        row for row in performance if (row["day_id"], row["scheduled_date"]) in eligible_slots
    ]
    recorded_sets = sum(len(row["sets"]) for row in observed)
    in_range = sum(row["in_range"] for row in observed)
    summary = report["summary"]

    def percentage(covered, total):
        return 100 * covered / total if total else None

    gap = max(gaps, key=gaps.get) if gaps else None
    return {
        "workout_pct": percentage(summary["linked_workouts"], summary["due_workouts"]),
        "set_pct": percentage(summary["covered_sets"], summary["planned_sets"]),
        "range_pct": percentage(in_range, recorded_sets),
        "in_range": in_range,
        "recorded_sets": recorded_sets,
        "missing_rir": sum(item["rir"] is None for row in observed for item in row["sets"]),
        "largest_gap": (gap, gaps[gap]) if gap and gaps[gap] else None,
        "weeks": [weeks[key] for key in sorted(weeks)],
    }
