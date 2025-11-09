import pandas as pd

class HistoryService:
    def __init__(self, df_sets: pd.DataFrame):
        self.df = df_sets.copy()
        self.df["SessionDate"] = pd.to_datetime(self.df["SessionDate"])
        self.df["Week"] = self.df["SessionDate"].dt.isocalendar().week
        self.df["Year"] = self.df["SessionDate"].dt.isocalendar().year

    def get_weeks(self):
        """Zwraca posortowaną listę dostępnych tygodni (Year, Week)."""
        self.df = self.df.dropna(subset=["Year", "Week"])
        self.df["Year"] = self.df["Year"].astype(int)
        self.df["Week"] = self.df["Week"].astype(int)
        df_unique = self.df[["Year", "Week"]].drop_duplicates()
        df_sorted = df_unique.sort_values(by=["Year", "Week"])
        return df_sorted.to_records(index=False)

    def get_week_sessions(self, year: int, week: int):
        """Zwraca wszystkie treningi z danego tygodnia, z listą ćwiczeń."""
        week_df = self.df[(self.df["Year"] == year) & (self.df["Week"] == week)]
        if week_df.empty:
            return None

        sessions = (
            week_df.groupby("SessionDate")
            .agg(
                total_sets=("ExerciseName", "count"),
                total_volume=("Volume", "sum")
            )
            .reset_index()
            .sort_values("SessionDate")
        )

        detailed_sessions = []
        for _, session_row in sessions.iterrows():
            session_date = session_row["SessionDate"]
            exercises = (
                week_df[week_df["SessionDate"] == session_date]
                .groupby("ExerciseName")
                .agg(
                    sets=("ExerciseName", "count"),
                    total_reps=("Repetitions", "sum"),
                    total_volume=("Volume", "sum")
                )
                .reset_index()
                .sort_values("ExerciseName")
            )

            detailed_sessions.append({
                "date": session_date,
                "total_sets": int(session_row["total_sets"]),
                "total_volume": int(session_row["total_volume"]),
                "exercises": exercises
            })

        return detailed_sessions
