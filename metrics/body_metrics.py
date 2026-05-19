from collections import defaultdict
from datetime import date, datetime
from statistics import mean
from typing import Any

from metrics.input import MetricsInput


EMPTY_BODY_METRICS = {
    "timeline": [],
    "global": {},
    "proportions": {},
    "recomposition": {},
    "insights": [],
    "deltas": {},
}


def to_date(value: Any) -> date:
    """Normalize date-like values to ``datetime.date`` for reliable joins."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    raise TypeError(f"Unsupported date value: {value!r}")


def _empty_body_metrics() -> dict[str, Any]:
    return {
        key: value.copy() if isinstance(value, (dict, list)) else value
        for key, value in EMPTY_BODY_METRICS.items()
    }


def _safe_ratio(a: float | None, b: float | None) -> float | None:
    if a and b:
        return round(a / b, 2)
    return None


def _calculate_proportion_ratios(
    latest_measurements: dict[str, float],
) -> dict[str, float]:
    ratios = {
        "chest_to_waist": _safe_ratio(
            latest_measurements.get("chest"),
            latest_measurements.get("waist"),
        ),
        "thigh_to_waist": _safe_ratio(
            latest_measurements.get("thigh"),
            latest_measurements.get("waist"),
        ),
        "biceps_to_waist": _safe_ratio(
            latest_measurements.get("biceps"),
            latest_measurements.get("waist"),
        ),
    }
    return {key: value for key, value in ratios.items() if value is not None}


def _calculate_recomposition_quality(
    delta_weight: float,
    delta_muscle: float,
) -> dict[str, Any]:
    if delta_weight == 0:
        return {
            "lean_mass_contribution_pct": 0,
            "recomposition_type": "stable",
        }

    lean_ratio = round((delta_muscle / delta_weight) * 100, 1)

    if delta_weight > 0:
        if lean_ratio > 75:
            recomp_type = "lean_bulk"
        elif lean_ratio > 25:
            recomp_type = "mixed_bulk"
        else:
            recomp_type = "fat_bulk"
    elif lean_ratio < -75:
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
    if len(timeline) < 2:
        return []

    insights = []
    first, last = timeline[0], timeline[-1]

    if first.get("weight") and last.get("weight"):
        diff = last["weight"] - first["weight"]
        if diff > 1:
            insights.append("Weight trending up - monitor lean vs fat gain.")
        elif diff < -1:
            insights.append("Weight trending down - ensure muscle preservation.")

    if first.get("fat_percentage") and last.get("fat_percentage"):
        if last["fat_percentage"] < first["fat_percentage"]:
            insights.append("Body fat decreasing - good recomposition.")
        elif last["fat_percentage"] > first["fat_percentage"]:
            insights.append("Body fat increasing - adjust diet/training.")

    return insights


def _calculate_metric_deltas(timeline: list[dict], column: str) -> float | None:
    values = [entry[column] for entry in timeline if entry.get(column) is not None]
    if len(values) < 2:
        return None
    return round(values[-1] - values[0], 2)


def compute_body_metrics(input: MetricsInput) -> dict:
    if not input.body_composition or len(input.body_composition) < 2:
        return _empty_body_metrics()

    records = sorted(input.body_composition, key=lambda entry: to_date(entry.date))

    measurements_by_date = defaultdict(dict)
    for measurement in input.body_measurements:
        measurements_by_date[to_date(measurement.date)][
            measurement.measurement_type.lower()
        ] = measurement.value

    weights = [record.weight for record in records if record.weight is not None]
    muscle_masses = [
        record.muscle_mass
        for record in records
        if record.muscle_mass is not None
    ]
    fat_pcts = [
        record.fat_percentage
        for record in records
        if record.fat_percentage is not None
    ]

    if not weights:
        return _empty_body_metrics()

    start_weight = weights[0]
    end_weight = weights[-1]

    dates = [to_date(record.date) for record in records]
    days = max((dates[-1] - dates[0]).days, 1)
    weeks = days / 7

    timeline = []
    for record in records:
        measurement_date = to_date(record.date)
        measurements = measurements_by_date.get(measurement_date, {})

        timeline.append(
            {
                "date": measurement_date,
                "weight": record.weight,
                "muscle_mass": record.muscle_mass,
                "fat_mass": record.fat_mass,
                "water_mass": record.water_mass,
                "fat_percentage": record.fat_percentage,
                "chest": measurements.get("chest"),
                "waist": measurements.get("waist"),
                "abdomen": measurements.get("abdomen"),
                "hips": measurements.get("hips"),
                "thigh": measurements.get("thigh"),
                "calf": measurements.get("calf"),
                "biceps": measurements.get("biceps"),
            }
        )

    global_metrics = {
        "start_weight": start_weight,
        "end_weight": end_weight,
        "total_weight_change": round(end_weight - start_weight, 2),
        "avg_weekly_weight_change": round((end_weight - start_weight) / weeks, 2),
        "avg_body_fat_pct": round(mean(fat_pcts), 2) if fat_pcts else None,
        "avg_muscle_mass": round(mean(muscle_masses), 2) if muscle_masses else None,
    }

    latest_date = to_date(records[-1].date)
    proportions = _calculate_proportion_ratios(
        measurements_by_date.get(latest_date, {})
    )

    valid_muscle = [record for record in records if record.muscle_mass is not None]
    delta_muscle = (
        valid_muscle[-1].muscle_mass - valid_muscle[0].muscle_mass
        if len(valid_muscle) >= 2
        else 0
    )
    recomposition = _calculate_recomposition_quality(
        delta_weight=end_weight - start_weight,
        delta_muscle=delta_muscle,
    )

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
        "insights": _generate_insights(timeline),
        "deltas": deltas,
    }
