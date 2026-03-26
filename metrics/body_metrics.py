"""
Body Metrics Engine (STABLE VERSION)

Fixes:
- string vs datetime issues
- empty dataset crashes
- inconsistent ordering
- unsafe indexing
"""

from collections import defaultdict
from statistics import mean
from datetime import datetime
from typing import Any

from metrics.input import MetricsInput


# ----------------------------
# SAFE DATE HANDLING
# ----------------------------
def to_date(x):
    if isinstance(x, str):
        return datetime.fromisoformat(x)
    return x


# ----------------------------
# PROPORTIONS
# ----------------------------
def _calculate_proportion_ratios(latest_measurements: dict[str, float]) -> dict[str, float]:
    ratios = {}

    def safe_ratio(a, b):
        if a and b:
            return round(a / b, 2)
        return None

    ratios["chest_to_waist"] = safe_ratio(
        latest_measurements.get("chest"),
        latest_measurements.get("waist"),
    )

    ratios["thigh_to_waist"] = safe_ratio(
        latest_measurements.get("thigh"),
        latest_measurements.get("waist"),
    )

    ratios["biceps_to_waist"] = safe_ratio(
        latest_measurements.get("biceps"),
        latest_measurements.get("waist"),
    )

    return {k: v for k, v in ratios.items() if v is not None}


# ----------------------------
# RECOMPOSITION
# ----------------------------
def _calculate_recomposition_quality(delta_weight: float, delta_muscle: float) -> dict[str, Any]:
    if delta_weight == 0:
        return {
            "lean_mass_contribution_pct": 0,
            "recomposition_type": "stable",
        }

    lean_ratio = round((delta_muscle / delta_weight) * 100, 1) if delta_weight else 0

    if delta_weight > 0:
        if lean_ratio > 75:
            recomp_type = "lean_bulk"
        elif lean_ratio > 25:
            recomp_type = "mixed_bulk"
        else:
            recomp_type = "fat_bulk"
    else:
        if lean_ratio < -75:
            recomp_type = "lean_cut"
        elif lean_ratio < -25:
            recomp_type = "mixed_cut"
        else:
            recomp_type = "fat_loss"

    return {
        "lean_mass_contribution_pct": lean_ratio,
        "recomposition_type": recomp_type,
    }


# ----------------------------
# INSIGHTS
# ----------------------------
def _generate_insights(timeline: list[dict]) -> list[str]:
    if len(timeline) < 2:
        return []

    insights = []
    first, last = timeline[0], timeline[-1]

    if first.get("weight") and last.get("weight"):
        diff = last["weight"] - first["weight"]
        if diff > 1:
            insights.append("Weight trending up — monitor lean vs fat gain.")
        elif diff < -1:
            insights.append("Weight trending down — ensure muscle preservation.")

    if first.get("fat_percentage") and last.get("fat_percentage"):
        if last["fat_percentage"] < first["fat_percentage"]:
            insights.append("Body fat decreasing — good recomposition.")
        elif last["fat_percentage"] > first["fat_percentage"]:
            insights.append("Body fat increasing — adjust diet/training.")

    return insights


# ----------------------------
# DELTAS SAFE
# ----------------------------
def _calculate_metric_deltas(timeline: list[dict], column: str) -> float | None:
    values = [e[column] for e in timeline if e.get(column) is not None]
    if len(values) < 2:
        return None
    return round(values[-1] - values[0], 2)


# ----------------------------
# MAIN FUNCTION
# ----------------------------
def compute_body_metrics(input: MetricsInput) -> dict:

    if not input.body_composition or len(input.body_composition) < 2:
        return {
            "timeline": [],
            "global": {},
            "proportions": {},
            "recomposition": {},
            "insights": [],
            "deltas": {},
        }

    records = sorted(input.body_composition, key=lambda x: to_date(x.date))

    measurements_by_date = defaultdict(dict)

    for day_measurements in input.body_measurements:
        for m in day_measurements:
            measurements_by_date[to_date(m.date)][m.measurement_type.lower()] = m.value

    weights = [r.weight for r in records if r.weight is not None]
    muscle_masses = [r.muscle_mass for r in records if r.muscle_mass is not None]
    fat_pcts = [r.fat_percentage for r in records if r.fat_percentage is not None]

    if not weights:
        return {
            "timeline": [],
            "global": {},
            "proportions": {},
            "recomposition": {},
            "insights": [],
            "deltas": {},
        }

    start_weight = weights[0]
    end_weight = weights[-1]

    dates = [to_date(r.date) for r in records]
    days = max((dates[-1] - dates[0]).days, 1)
    weeks = days / 7

    # ----------------------------
    # TIMELINE
    # ----------------------------
    timeline = []

    for r in records:
        d = to_date(r.date)
        m = measurements_by_date.get(d, {})

        timeline.append({
            "date": d,
            "weight": r.weight,
            "muscle_mass": r.muscle_mass,
            "fat_mass": r.fat_mass,
            "water_mass": r.water_mass,
            "fat_percentage": r.fat_percentage,
            "chest": m.get("chest"),
            "waist": m.get("waist"),
            "abdomen": m.get("abdomen"),
            "hips": m.get("hips"),
            "thigh": m.get("thigh"),
            "calf": m.get("calf"),
            "biceps": m.get("biceps"),
        })

    # ----------------------------
    # GLOBAL
    # ----------------------------
    global_metrics = {
        "start_weight": start_weight,
        "end_weight": end_weight,
        "total_weight_change": round(end_weight - start_weight, 2),
        "avg_weekly_weight_change": round((end_weight - start_weight) / weeks, 2),
        "avg_body_fat_pct": round(mean(fat_pcts), 2) if fat_pcts else None,
        "avg_muscle_mass": round(mean(muscle_masses), 2) if muscle_masses else None,
    }

    # ----------------------------
    # PROPORTIONS
    # ----------------------------
    latest_date = to_date(records[-1].date)
    latest_measurements = measurements_by_date.get(latest_date, {})
    proportions = _calculate_proportion_ratios(latest_measurements)

    # ----------------------------
    # RECOMPOSITION
    # ----------------------------
    delta_weight = end_weight - start_weight

    valid_muscle = [r for r in records if r.muscle_mass is not None]
    delta_muscle = (
        valid_muscle[-1].muscle_mass - valid_muscle[0].muscle_mass
        if len(valid_muscle) >= 2
        else 0
    )

    recomposition = _calculate_recomposition_quality(delta_weight, delta_muscle)

    # ----------------------------
    # INSIGHTS
    # ----------------------------
    insights = _generate_insights(timeline)

    # ----------------------------
    # DELTAS
    # ----------------------------
    deltas = {
        "weight": _calculate_metric_deltas(timeline, "weight"),
        "muscle_mass": _calculate_metric_deltas(timeline, "muscle_mass"),
        "fat_percentage": _calculate_metric_deltas(timeline, "fat_percentage"),
        "chest": _calculate_metric_deltas(timeline, "chest"),
        "waist": _calculate_metric_deltas(timeline, "waist"),
        "thigh": _calculate_metric_deltas(timeline, "thigh"),
        "biceps": _calculate_metric_deltas(timeline, "biceps"),
    }

    return {
        "timeline": timeline,
        "global": global_metrics,
        "proportions": proportions,
        "recomposition": recomposition,
        "insights": insights,
        "deltas": deltas,
    }