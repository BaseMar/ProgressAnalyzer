from collections import defaultdict
from statistics import mean
from metrics.input import MetricsInput


def compute_body_metrics(input: MetricsInput) -> dict:
    if not input.body_composition or len(input.body_composition) < 2:
        return {}

    records = sorted(input.body_composition, key=lambda x: x.date)
    measurements_by_date = defaultdict(dict)

    for day_measurements in input.body_measurements:
        for m in day_measurements:
            measurements_by_date[m.date][m.measurement_type.lower()] = m.value
    
    weights = [r.weight for r in records]
    muscle_mass = [r.muscle_mass for r in records if r.muscle_mass is not None]
    fat_mass = [r.fat_mass for r in records if r.fat_mass is not None]
    water_mass = [r.water_mass for r in records if r.water_mass is not None]
    fat_pct = [r.fat_percentage for r in records if r.fat_percentage is not None]    

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

    return {
        "timeline": timeline,
        "global": global_metrics,
    }
