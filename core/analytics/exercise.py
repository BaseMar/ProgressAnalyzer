import pandas as pd
from .base import require_columns, add_volume_column, compute_est_1rm, pct_change

class ExerciseAnalytics:
    def __init__(self, df_sets: pd.DataFrame):
        require_columns(df_sets, ["SessionDate", "ExerciseName", "Weight", "Repetitions", "SetNumber"])
        self.df = df_sets.copy()
        self.df["SessionDate"] = pd.to_datetime(self.df["SessionDate"])
        self.df = add_volume_column(self.df)
    
    def list_exercises(self) -> list[str]:
        return sorted(self.df["ExerciseName"].dropna().unique().tolist())

    def filter_exercise(self, exercise_name: str) -> pd.DataFrame:
        return self.df[self.df["ExerciseName"] == exercise_name].copy()

    def compute_session_summary(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        df = df_ex.copy()
        df["Est1RM"] = df.apply(lambda r: compute_est_1rm(r["Weight"], r["Repetitions"]), axis=1)
        df["TotalVolume"] = df["Weight"] * df["Repetitions"]

        session_summary = (
            df.groupby("SessionDate")
            .agg(Est1RM=("Est1RM", "max"), TotalVolume=("TotalVolume", "sum"), Weight=("Weight", "mean"))
            .reset_index()
            .sort_values("SessionDate")
        )
        return session_summary

    def compute_kpis(self, session_summary: pd.DataFrame) -> dict:
        if session_summary.empty:
            return {"latest_1rm": 0.0, "start_1rm": 0.0, "progress": 0.0, "avg_weight": 0.0}
        latest_1rm = float(session_summary["Est1RM"].iloc[-1])
        start_1rm = float(session_summary["Est1RM"].iloc[0])
        progress = pct_change(latest_1rm, start_1rm)
        avg_weight = float(session_summary["Weight"].mean())
        return {
            "latest_1rm": round(latest_1rm, 2),
            "start_1rm": round(start_1rm, 2),
            "progress": round(progress, 2),
            "avg_weight": round(avg_weight, 2)
        }

    def compute_history_table(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        df = df_ex.copy()
        df = add_volume_column(df)
        df_summary = (
            df.groupby("SessionDate")
            .agg(SeriesCount=("SetNumber", "count"),
                 TotalReps=("Repetitions", "sum"),
                 AvgWeight=("Weight", "mean"),
                 Volume=("Volume", "sum"))
            .reset_index()
            .sort_values("SessionDate")
        )
        df_summary["SessionDate"] = df_summary["SessionDate"].dt.date
        df_summary["AvgWeight"] = df_summary["AvgWeight"].round(1)
        df_summary["Volume"] = df_summary["Volume"].round(1)
        return df_summary
