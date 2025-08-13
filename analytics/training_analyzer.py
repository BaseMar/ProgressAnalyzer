import pandas as pd

def calculate_intensity_per_muscle_group(mapped_df: pd.DataFrame) -> pd.DataFrame:
    """Oblicza średnią intensywność (ciężar/serię) na każdą grupę mięśniową w ujęciu tygodniowym."""

    mapped_df["Rok"] = mapped_df["Data"].dt.isocalendar().year
    mapped_df["Tydzien"] = mapped_df["Data"].dt.isocalendar().week

    grouped = (
        mapped_df
        .groupby(["Partia", "Rok", "Tydzien"])
        .apply(lambda x: (x["Ciezar"] * x["Powtorzenia"]).sum() / x["Powtorzenia"].sum())
        .reset_index(name="Intensywnosc")
    )

    grouped["Data"] = grouped.apply(lambda row: pd.to_datetime(f'{row["Rok"]}-W{int(row["Tydzien"]):02}-1', format='%G-W%V-%u'), axis=1)

    return grouped

def calculate_1rm_per_muscle_group(mapped_df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """
    Oblicza średnie 1RM dla grupy mięśniowej w określonym przedziale czasowym.
    freq: "W" = tygodniowo, "M" = miesięcznie
    """

    mapped_df["1RM"] = mapped_df["Ciezar"] * (1 + mapped_df["Powtorzenia"] / 30)
    mapped_df["Data"] = pd.to_datetime(mapped_df["Data"])
    mapped_df.set_index("Data", inplace=True)

    grouped = (
        mapped_df.groupby(["Partia", pd.Grouper(freq=freq)])["1RM"]
        .mean()
        .reset_index()
    )

    return grouped

def calculate_last_exercise_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    results = []
    for exercise in df["Cwiczenie"].unique():
        ex_df = df[df["Cwiczenie"] == exercise].sort_values("Data")
        if ex_df.empty:
            continue

        last_df = ex_df[ex_df["Data"] == ex_df["Data"].max()]
        prev_df = ex_df[ex_df["Data"] < ex_df["Data"].max()]
        if not prev_df.empty:
            prev_df = prev_df[prev_df["Data"] == prev_df["Data"].max()]

        def summarize(data):
            if data.empty:
                return None
            total_volume = (data["Ciezar"] * data["Powtorzenia"]).sum()
            return {
                "Ćwiczenie": exercise,
                "Maks. ciężar (kg)": data["Ciezar"].max(),
                "Objętość (kg)": total_volume,
                "Śr. ciężar / powt. (kg)": total_volume / data["Powtorzenia"].sum(),
                "Szacowane 1RM (kg)": data["Ciezar"].max() * (1 + (data["Powtorzenia"].mean() / 30))
            }

        current_summary = summarize(last_df)
        prev_summary = summarize(prev_df)

        if current_summary:
            if prev_summary:
                for col in ["Maks. ciężar (kg)", "Objętość (kg)", "Śr. ciężar / powt. (kg)", "Szacowane 1RM (kg)"]:
                    change_col = f"Zmiana {col} [%]"
                    if prev_summary[col] != 0:
                        current_summary[change_col] = ((current_summary[col] - prev_summary[col]) / prev_summary[col]) * 100
                    else:
                        current_summary[change_col] = None
            results.append(current_summary)

    summary_df = pd.DataFrame(results)

    # Wymuszenie float i zaokrąglenie
    num_cols = summary_df.select_dtypes(include=["number"]).columns
    summary_df[num_cols] = summary_df[num_cols].astype(float).round(2)

    return summary_df

def color_change(val):
    """Koloruje wartości procentowe: zielony = wzrost, czerwony = spadek, szary = brak zmian/danych."""
    if pd.isna(val):
        return "color: gray;"
    if val > 0:
        return "color: green; font-weight: bold;"
    elif val < 0:
        return "color: red; font-weight: bold;"
    else:
        return "color: gray;"
