import pandas as pd

def filter_training_data(df: pd.DataFrame, date_start, date_end, selected_exercise):
    mask = (df['Data'] >= date_start) & (df['Data'] <= date_end)
    if selected_exercise != "Wszystkie":
        mask &= df['Cwiczenie'] == selected_exercise
    return df[mask]