import pandas as pd

def calculate_intensity_per_muscle_group(mapped_df: pd.DataFrame) -> pd.DataFrame:
    """Oblicza średnią intensywność (ciężar/serię) na każdą grupę mięśniową."""

    grouped = mapped_df.groupby(["Partia", "Data"]).apply(lambda x: (x["Ciezar"] * x["Powtorzenia"]).sum() / x["Powtorzenia"].sum()).reset_index(name="Intensywnosc")

    return grouped