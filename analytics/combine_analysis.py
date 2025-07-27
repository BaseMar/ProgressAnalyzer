from datetime import datetime, timedelta

def join_measurements_by_date(body_composition_list, body_measurements_list, tolerance_days=1):
    combined_results = []
    used_measurements = set()

    for comp in body_composition_list:
        comp_date = comp["DataPomiaru"]
        closest = None
        min_diff = timedelta(days=tolerance_days + 1)

        for i, meas in enumerate(body_measurements_list):
            if i in used_measurements:
                continue

            meas_date = meas["Data"]
            diff = abs(comp_date - meas_date)

            if diff <= timedelta(days=tolerance_days) and diff < min_diff:
                closest = (i, meas)
                min_diff = diff

        if closest:
            idx, matched_measurement = closest
            used_measurements.add(idx)

            combined_results.append({
                "Data": comp_date,
                **comp,
                **matched_measurement
            })

    return combined_results

from datetime import timedelta

def merge_body_data_with_tolerance(body_composition, body_measurements, max_days_diff=1):
    merged = []

    for comp in body_composition:
        data_comp = comp["DataPomiaru"]

        # Szukamy najbliższego pomiaru obwodów
        best_match = None
        min_diff = timedelta(days=max_days_diff + 1)

        for meas in body_measurements:
            data_meas = meas["DataPomiaru"]
            diff = abs(data_comp - data_meas)

            if diff <= timedelta(days=max_days_diff) and diff < min_diff:
                best_match = meas
                min_diff = diff

        if best_match:
            merged_record = {**comp, **best_match}
            merged.append(merged_record)

    return merged

