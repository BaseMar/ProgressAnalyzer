from statistics import mean
from metrics.input import MetricsInput


def compute_body_metrics(input: MetricsInput) -> dict:
    if not input.body_composition or len(input.body_composition) < 2:
        return {}

    records = sorted(input.body_composition, key=lambda x: x.date)

    weights = [r.weight for r in records]
    fat_pct = [r.fat_percentage for r in records if r.fat_percentage is not None]
    muscle_mass = [r.muscle_mass for r in records if r.muscle_mass is not None]

    start_weight = weights[0]
    end_weight = weights[-1]

    days = max((records[-1].date - records[0].date).days, 1)
    weeks = days / 7

    global_metrics = {
        "start_weight": start_weight,
        "end_weight": end_weight,
        "total_weight_change": round(end_weight - start_weight, 2),
        "avg_weekly_weight_change": round((end_weight - start_weight) / weeks, 2),
        "avg_body_fat_pct": round(mean(fat_pct), 2) if fat_pct else None,
        "avg_muscle_mass": round(mean(muscle_mass), 2) if muscle_mass else None,
    }

    timeline = [
        {
            "date": r.date,
            "weight": r.weight,
            "fat_percentage": r.fat_percentage,
            "muscle_mass": r.muscle_mass,
        }
        for r in records
    ]

    return {
        "timeline": timeline,
        "global": global_metrics,
    }
