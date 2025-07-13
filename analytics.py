import pandas as pd

def filter_training_data(df, start_date, end_date, exercise=None):
    df['Data'] = pd.to_datetime(df['Data'])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    filtered = df[(df['Data'] >= start_date) & (df['Data'] <= end_date)]
    if exercise and exercise != "Wszystkie":
        filtered = filtered[filtered['Cwiczenie'] == exercise]
    return filtered

def summarize_measurements(df, metric):
    df['Data'] = pd.to_datetime(df['Data'])
    values = df[metric].dropna()

    if values.empty:
        return None

    first = values.iloc[0]
    last = values.iloc[-1]
    min_val = values.min()
    max_val = values.max()
    avg_val = values.mean()

    percent_change = ((last - first) / abs(first) * 100) if first != 0 else 0
    trend_icon = "⬆️" if last > first else "⬇️" if last < first else "➡️"

    return {
        "first": first,
        "last": last,
        "min": min_val,
        "max": max_val,
        "avg": avg_val,
        "percent_change": percent_change,
        "trend_icon": trend_icon
    }
