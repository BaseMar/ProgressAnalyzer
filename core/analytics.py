import pandas as pd

class TrainingAnalytics:
    """
    Klasa dostarczająca funkcje analityczne do przetwarzania danych treningowych.
    """

    def __init__(self, df_sets: pd.DataFrame):
        if df_sets is None or df_sets.empty:
            raise ValueError("DataFrame z seriami treningowymi jest pusty lub None.")
        
        self.df_sets = df_sets.copy()
        self.df_sets["SessionDate"] = pd.to_datetime(self.df_sets["SessionDate"])
        
        self.df_sets["Volume"] = self.df_sets["Weight"] * self.df_sets["Repetitions"]
        self.df_sets["Intensity"] = self.df_sets["Volume"]

    def weekly_agg(self, col: str, agg_func="mean") -> dict:
        """
        Uniwersalna funkcja agregująca kolumnę po tygodniach z procentową zmianą.
        
        agg_func: 'mean' dla średniej, 'sum' dla sumy (np. łączna objętość)
        """
        df = self.df_sets.copy()
        df["Week"] = df["SessionDate"].dt.isocalendar().week
        df["Year"] = df["SessionDate"].dt.isocalendar().year

        if agg_func == "mean":
            weekly = df.groupby(["Year", "Week"])[col].mean()
        elif agg_func == "sum":
            weekly = df.groupby(["Year", "Week"])[col].sum()
        else:
            raise ValueError("agg_func musi być 'mean' lub 'sum'")

        weekly = weekly.reset_index().sort_values(["Year", "Week"])

        if weekly.empty:
            return {"current": 0, "previous": 0, "change": 0}
        elif len(weekly) == 1:
            current = weekly.iloc[-1][col]
            return {"current": current, "previous": 0, "change": 0}

        current = weekly.iloc[-1][col]
        previous = weekly.iloc[-2][col]
        change = ((current - previous) / previous * 100) if previous != 0 else 0

        return {"current": round(current, 2), "previous": round(previous, 2), "change": round(change, 2)}

    def kpi_summary(self) -> dict:
        """Zwraca podstawowe statystyki: liczba sesji, średnia intensywność (waga*powtórzenia)."""
        total_sessions = self.df_sets["SessionDate"].nunique()
        avg_intensity = self.df_sets["Intensity"].mean()
        return {
            "sessions": total_sessions,
            "avg_intensity": round(avg_intensity, 2),
        }
