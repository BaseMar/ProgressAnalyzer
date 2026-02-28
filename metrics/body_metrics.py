"""
Body Metrics Engine

Responsible for computing body composition and measurement metrics from raw input data.
Handles all calculations related to weight changes, recomposition quality, proportions,
and trend analysis.
"""

from collections import defaultdict
from statistics import mean
from typing import Any

from metrics.input import MetricsInput


def _calculate_proportion_ratios(latest_measurements: dict[str, float]) -> dict[str, float]:
    """Calculate body proportion ratios from latest measurements.
    
    Proportions are used for recomposition analysis and body balance assessment.
    Only calculates ratios where both measurements exist.
    """
    ratios = {}
    
    # Chest to waist ratio (indicator of upper body development)
    if "chest" in latest_measurements and "waist" in latest_measurements:
        chest, waist = latest_measurements["chest"], latest_measurements["waist"]
        if chest and waist:
            ratios["chest_to_waist"] = round(chest / waist, 2)
    
    # Thigh to waist ratio (indicator of leg development)
    if "thigh" in latest_measurements and "waist" in latest_measurements:
        thigh, waist = latest_measurements["thigh"], latest_measurements["waist"]
        if thigh and waist:
            ratios["thigh_to_waist"] = round(thigh / waist, 2)
    
    # Biceps to waist ratio (indicator of arm development)
    if "biceps" in latest_measurements and "waist" in latest_measurements:
        biceps, waist = latest_measurements["biceps"], latest_measurements["waist"]
        if biceps and waist:
            ratios["biceps_to_waist"] = round(biceps / waist, 2)
    
    return ratios


def _calculate_recomposition_quality(
    delta_weight: float, delta_muscle: float
) -> dict[str, Any]:
    """Calculate recomposition quality metrics.
    
    Returns the percentage of weight change attributable to lean mass,
    and classification of the recomposition direction.
    """
    if delta_weight == 0:
        return {
            "lean_mass_contribution_pct": 0,
            "recomposition_type": "stable",
        }
    
    lean_ratio = (delta_muscle / delta_weight * 100) if delta_weight else 0
    lean_ratio = round(lean_ratio, 1)
    
    # Classify recomposition type
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


def _generate_insights(timeline: list[dict]) -> list[str]:
    """Generate actionable insights from body metrics trends."""
    if not timeline or len(timeline) < 2:
        return []
    
    insights = []
    first, last = timeline[0], timeline[-1]
    
    # Weight trend insight
    if "weight" in first and "weight" in last:
        weight_change = last["weight"] - first["weight"]
        if weight_change > 1:
            insights.append("Weight trending up — ensure muscle development is intended.")
        elif weight_change < -1:
            insights.append("Weight trending down — monitor muscle mass preservation.")
    
    # Body fat trend insight
    if "fat_percentage" in first and "fat_percentage" in last:
        if last["fat_percentage"] < first["fat_percentage"]:
            insights.append("Body fat decreasing — good recomposition trajectory.")
        elif last["fat_percentage"] > first["fat_percentage"]:
            insights.append("Body fat increasing — consider training/diet adjustments.")
    
    # Waist vs thigh balance
    if "waist" in first and "thigh" in first and "waist" in last and "thigh" in last:
        waist_change = last["waist"] - first["waist"]
        thigh_change = last["thigh"] - first["thigh"]
        
        if waist_change > thigh_change + 1:
            insights.append(
                "Waist growing faster than legs — consider lower-body hypertrophy focus."
            )
        elif thigh_change > waist_change + 1:
            insights.append(
                "Legs developing well relative to core — excellent proportionality trend."
            )
    
    # Muscle mass trend
    if "muscle_mass" in first and "muscle_mass" in last:
        muscle_change = last["muscle_mass"] - first["muscle_mass"]
        if muscle_change > 1:
            insights.append("Muscle mass increasing — strength gains are well-supported.")
        elif muscle_change < -1:
            insights.append("Muscle mass decreasing — increase protein/training volume.")
    
    return insights


def _calculate_metric_deltas(timeline: list[dict], column: str) -> float | None:
    """Calculate the change in a metric from first to last measurement."""
    if not timeline or column not in timeline[0] or column not in timeline[-1]:
        return None
    
    values = [e[column] for e in timeline if e.get(column) is not None]
    if len(values) < 2:
        return None
    
    return round(values[-1] - values[0], 2)


def compute_body_metrics(input: MetricsInput) -> dict:
    """Compute all body composition and measurement metrics.
    
    Args:
        input: MetricsInput containing body composition and measurement records.
    
    Returns:
        Dictionary with keys:
        - timeline: List of timestamped metrics with calculations
        - global: Global summary metrics across entire timeline
        - proportions: Body proportion ratios from latest measurements
        - recomposition: Recomposition quality metrics
        - insights: List of generated insights from trends
        - deltas: Change values for each metric type
    """
    if not input.body_composition or len(input.body_composition) < 2:
        return {
            "timeline": [],
            "global": {},
            "proportions": {},
            "recomposition": {},
            "insights": [],
            "deltas": {},
        }

    records = sorted(input.body_composition, key=lambda x: x.date)
    measurements_by_date = defaultdict(dict)

    for day_measurements in input.body_measurements:
        for m in day_measurements:
            measurements_by_date[m.date][m.measurement_type.lower()] = m.value
    
    weights = [r.weight for r in records]
    muscle_masses = [r.muscle_mass for r in records if r.muscle_mass is not None]
    fat_masses = [r.fat_mass for r in records if r.fat_mass is not None]
    water_masses = [r.water_mass for r in records if r.water_mass is not None]
    fat_pcts = [r.fat_percentage for r in records if r.fat_percentage is not None]    

    start_weight = weights[0]
    end_weight = weights[-1]

    days = max((records[-1].date - records[0].date).days, 1)
    weeks = days / 7

    # Build timeline
    timeline = []
    for r in records:
        m = measurements_by_date.get(r.date, {})
        timeline.append({
            "date": r.date,
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

    # Global metrics
    global_metrics = {
        "start_weight": start_weight,
        "end_weight": end_weight,
        "total_weight_change": round(end_weight - start_weight, 2),
        "avg_weekly_weight_change": round((end_weight - start_weight) / weeks, 2),
        "avg_body_fat_pct": round(mean(fat_pcts), 2) if fat_pcts else None,
        "avg_muscle_mass": round(mean(muscle_masses), 2) if muscle_masses else None,
    }

    # Extract latest measurements for proportions
    latest_measurements = measurements_by_date.get(records[-1].date, {})
    proportions = _calculate_proportion_ratios(latest_measurements)

    # Calculate recomposition quality
    delta_weight = end_weight - start_weight
    delta_muscle = (muscle_masses[-1] - muscle_masses[0]) if muscle_masses else 0
    recomposition = _calculate_recomposition_quality(delta_weight, delta_muscle)

    # Generate insights
    insights = _generate_insights(timeline)

    # Calculate metric deltas
    deltas = {
        "weight": _calculate_metric_deltas(timeline, "weight"),
        "muscle_mass": _calculate_metric_deltas(timeline, "muscle_mass"),
        "fat_percentage": _calculate_metric_deltas(timeline, "fat_percentage"),
        "chest": _calculate_metric_deltas(timeline, "chest"),
        "waist": _calculate_metric_deltas(timeline, "waist"),
        "thigh": _calculate_metric_deltas(timeline, "thigh"),
        "biceps": _calculate_metric_deltas(timeline, "biceps"),
    }

    # add a delta for the chest/waist ratio if enough data exists
    def _calculate_ratio_delta(timeline: list[dict], num: str, den: str) -> float | None:
        vals = []
        for e in timeline:
            n = e.get(num)
            d = e.get(den)
            if n is None or d in (None, 0):
                continue
            vals.append(n / d)
        if len(vals) < 2:
            return None
        return round(vals[-1] - vals[0], 2)

    deltas["chest_to_waist"] = _calculate_ratio_delta(timeline, "chest", "waist")

    return {
        "timeline": timeline,
        "global": global_metrics,
        "proportions": proportions,
        "recomposition": recomposition,
        "insights": insights,
        "deltas": deltas,
    }
