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

    def weekly_agg(self, col: str | None = None, agg_func="mean") -> dict:
        """
        Uniwersalna funkcja agregująca dane tygodniowe z procentową zmianą.
        - 'mean'  → średnia wartości (np. intensywność)
        - 'sum'   → suma wartości (np. objętość)
        - 'sets_per_session' → średnia liczba serii na sesję
        """
        df = self.df_sets.copy()
        df["Week"] = df["SessionDate"].dt.isocalendar().week
        df["Year"] = df["SessionDate"].dt.isocalendar().year

        if agg_func == "mean":
            weekly = df.groupby(["Year", "Week"])[col].mean().reset_index(name="Value")
        elif agg_func == "sum":
            weekly = df.groupby(["Year", "Week"])[col].sum().reset_index(name="Value")
        elif agg_func == "sets_per_session":
            weekly = (
                df.groupby(["Year", "Week"])
                .agg(total_sets=("SessionDate", "count"),
                     total_sessions=("SessionDate", "nunique"))
                .reset_index()
            )
            weekly["Value"] = weekly["total_sets"] / weekly["total_sessions"]
        else:
            raise ValueError("agg_func musi być 'mean', 'sum' lub 'sets_per_session'")

        weekly = weekly.sort_values(["Year", "Week"]).reset_index(drop=True)

        if weekly.empty:
            return {"current": 0, "previous": 0, "change": 0}
        elif len(weekly) == 1:
            current = weekly.iloc[-1]["Value"]
            return {"current": current, "previous": 0, "change": 0}

        current = weekly.iloc[-1]["Value"]
        previous = weekly.iloc[-2]["Value"]
        change = ((current - previous) / previous * 100) if previous else 0

        return {
            "current": round(current, 2),
            "previous": round(previous, 2),
            "change": round(change, 2),
        }

    def kpi_summary(self) -> dict:
        """Zwraca podstawowe statystyki: liczba sesji, średnia intensywność (waga*powtórzenia)."""
        total_sessions = self.df_sets["SessionDate"].nunique()
        avg_intensity = self.df_sets["Intensity"].mean()
        sets_per_session = (len(self.df_sets) / total_sessions if total_sessions > 0 else 0)
        
        return {
            "sessions": total_sessions,
            "avg_intensity": round(avg_intensity, 2),
            "avg_sets_per_session": round(sets_per_session, 2),
        }
