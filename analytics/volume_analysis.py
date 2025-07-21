import pandas as pd

def calculate_volume_per_muscle(df, exercise_to_groups):
    df["Volume"] = df["Powtorzenia"] * df["Ciezar"]
    group_volume = {}

    for index, row in df.iterrows():
        exercise = row["Cwiczenie"]
        volume = row["Volume"]
        date = row["Data"]
        groups = exercise_to_groups.get(exercise, [])

        for group in groups:
            if group not in group_volume:
                group_volume[group] = {}
            group_volume[group][date] = group_volume[group].get(date, 0) + volume

    return {group: pd.Series(data).sort_index() for group, data in group_volume.items()}

def analyze_training_volume(series, weeks_window=4):
    series = series.astype(float)
    nonzero_series = series[series > 0]

    if len(nonzero_series) < weeks_window + 1:
        return "Za mało danych do analizy"

    recent_mean = nonzero_series.iloc[-(weeks_window + 1):-1].mean()
    current = nonzero_series.iloc[-1]

    if recent_mean == 0:
        return "Brak wcześniejszych danych do porównania"

    change = (current - recent_mean) / recent_mean

    if change < -0.2:
        return "Możliwe niedotrenowanie – objętość spadła >20%"
    elif change > 0.3:
        return "Ryzyko przetrenowania – gwałtowny wzrost objętości >30%"
    else:
        return "Objętość stabilna"