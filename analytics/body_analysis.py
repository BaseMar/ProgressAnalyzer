def summarize_measurements(df, metric: str):
    if df.empty or metric not in df.columns:
        return None

    metric_values = df[metric].dropna()
    if metric_values.empty:
        return None

    min_val = metric_values.min()
    max_val = metric_values.max()
    avg_val = metric_values.mean()
    percent_change = ((metric_values.iloc[-1] - metric_values.iloc[0]) / metric_values.iloc[0]) * 100 if len(metric_values) > 1 else 0
    trend_icon = "🔺" if percent_change > 0 else "🔻" if percent_change < 0 else "➖"

    return {
        "min": min_val,
        "max": max_val,
        "avg": avg_val,
        "percent_change": percent_change,
        "trend_icon": trend_icon
    }