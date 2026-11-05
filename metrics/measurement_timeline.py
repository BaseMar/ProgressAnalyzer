"""Recorded body values by actual date, including first and measurement-only logs."""
from metrics.body_metrics import to_date


def measurement_timeline(input_data):
    days = {}
    for item in input_data.body_composition:
        day = to_date(item.date)
        row = days.setdefault(day, {"date": day})
        for field in ("weight", "muscle_mass", "fat_mass", "water_mass", "fat_percentage"):
            row[field] = getattr(item, field)
    for item in input_data.body_measurements:
        day = to_date(item.date)
        days.setdefault(day, {"date": day})[item.measurement_type.lower()] = item.value
    return [days[day] for day in sorted(days)]
