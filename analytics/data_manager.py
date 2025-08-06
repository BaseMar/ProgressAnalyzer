from datetime import timedelta
from typing import Dict
import pandas as pd

def merge_body_data_with_tolerance(body_composition: dict, body_measurements: dict, max_days_diff=1)-> Dict[str, str]:
        """Łączy dane z bazy dla obwodów ciała i składu ciała"""
        merged = []

        for comp in body_composition:
            data_comp = comp["DataPomiaru"]

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

def filter_training_data(df: pd.DataFrame, date_start, date_end, selected_exercise):
    mask = (df['Data'] >= date_start) & (df['Data'] <= date_end)
    if selected_exercise != "Wszystkie":
        mask &= df['Cwiczenie'] == selected_exercise
    return df[mask]
    