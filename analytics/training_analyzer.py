from datetime import datetime
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

def calculate_sets_per_muscle_group(mapped_df: pd.DataFrame) -> pd.DataFrame:
    """
    Zlicza liczbę serii na każdą grupę mięśniową w ujęciu tygodniowym.
    Zwraca DataFrame z kolumnami ['Partia', 'Rok', 'Tydzien', 'Serie'].
    """
    df = mapped_df.copy()
    df['Data'] = pd.to_datetime(df['Data'])
    df['Rok'] = df['Data'].dt.isocalendar().year
    df['Tydzien'] = df['Data'].dt.isocalendar().week

    grouped = df.groupby(['Partia', 'Rok', 'Tydzien']) \
                .size() \
                .reset_index(name='Serie')

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
