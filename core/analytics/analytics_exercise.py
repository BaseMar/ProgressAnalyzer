import pandas as pd

class ExerciseAnalytics:
    """
    Logika analityczna dedykowana dla zakładki Analiza Ćwiczeń.
    Oddzielona od UI oraz reszty dashboardu.
    """

    def __init__(self, df_sets: pd.DataFrame):
        if df_sets is None or df_sets.empty:
            raise ValueError("DataFrame z seriami treningowymi jest pusty lub None.")

        self.df = df_sets.copy()
        self.df["SessionDate"] = pd.to_datetime(self.df["SessionDate"])
        self.df["Volume"] = self.df["Weight"] * self.df["Repetitions"]

    def list_exercises(self) -> list[str]:
        """Zwraca posortowaną listę dostępnych ćwiczeń."""
        return sorted(self.df["ExerciseName"].unique().tolist())

    def filter_exercise(self, exercise_name: str) -> pd.DataFrame:
        """Zwraca DataFrame tylko dla wybranego ćwiczenia."""
        return self.df[self.df["ExerciseName"] == exercise_name].copy()

    def compute_session_summary(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        """
        Podstawowa agregacja per sesja:
        - Est1RM (max)
        - TotalVolume
        - Avg working weight
        """
        df_ex = df_ex.copy()
        df_ex["Est1RM"] = df_ex["Weight"] * (1 + df_ex["Repetitions"] / 30)
        df_ex["TotalVolume"] = df_ex["Repetitions"] * df_ex["Weight"]

        session_summary = (
            df_ex.groupby("SessionDate")
            .agg({
                "Est1RM": "max",
                "TotalVolume": "sum",
                "Weight": "mean"
            })
            .reset_index()
            .sort_values("SessionDate")
        )

        return session_summary
    
    def compute_kpis(self, session_summary: pd.DataFrame) -> dict:
        """Oblicza KPI dla ćwiczenia."""
        latest_1rm = session_summary["Est1RM"].iloc[-1]
        start_1rm = session_summary["Est1RM"].iloc[0]
        progress = (latest_1rm - start_1rm) / start_1rm * 100 if start_1rm > 0 else 0
        avg_weight = session_summary["Weight"].mean()

        return {
            "latest_1rm": latest_1rm,
            "start_1rm": start_1rm,
            "progress": progress,
            "avg_weight": avg_weight
        }

    def compute_history_table(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        """Tabela historii danego ćwiczenia (jedna linia = jedna sesja)."""
        df_summary = (
            df_ex.groupby("SessionDate")
            .agg(
                SeriesCount=("SetNumber", "count"),
                TotalReps=("Repetitions", "sum"),
                AvgWeight=("Weight", "mean"),
                Volume=("Volume", "sum")
            )
            .reset_index()
            .sort_values("SessionDate")
        )

        df_summary["SessionDate"] = df_summary["SessionDate"].dt.date
        df_summary["AvgWeight"] = df_summary["AvgWeight"].round(1)
        df_summary["Volume"] = df_summary["Volume"].round(1)

        return df_summary
    