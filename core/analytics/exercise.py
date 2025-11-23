import pandas as pd

from .base import add_volume_column, compute_est_1rm, pct_change, require_columns


class ExerciseAnalytics:
    """Analytics engine for per-exercise training data.

    Accepts a DataFrame of workout sets and provides methods to compute KPIs,
    session summaries and progress tracking for individual exercises.
    """

    def __init__(self, df_sets: pd.DataFrame):
        """Initialize with a DataFrame of workout sets.

        Required columns: SessionDate, ExerciseName, Weight, Repetitions, SetNumber.
        """
        require_columns(
            df_sets,
            ["SessionDate", "ExerciseName", "Weight", "Repetitions", "SetNumber"],
        )
        self.df = df_sets.copy()
        self.df["SessionDate"] = pd.to_datetime(self.df["SessionDate"])
        self.df = add_volume_column(self.df)

    def list_exercises(self) -> list[str]:
        """Return a sorted list of unique exercise names from the dataset."""
        return sorted(self.df["ExerciseName"].dropna().unique().tolist())

    def filter_exercise(self, exercise_name: str) -> pd.DataFrame:
        """Filter the dataset to a single exercise, returning a copy of matching rows."""
        return self.df[self.df["ExerciseName"] == exercise_name].copy()

    def compute_session_summary(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        """Compute per-session summary metrics for the given exercise DataFrame.

        Returns a DataFrame grouped by SessionDate with Est1RM (max), TotalVolume
        and average Weight per session.
        """
        df = df_ex.copy()
        # compute estimated 1RM and volume using the local exercise slice (not the whole dataset)
        df["Est1RM"] = compute_est_1rm(df["Weight"], df["Repetitions"])
        df["TotalVolume"] = df["Weight"] * df["Repetitions"]

        session_summary = (
            df.groupby("SessionDate", as_index=False)
            .agg(
                Est1RM=("Est1RM", "max"),
                TotalVolume=("TotalVolume", "sum"),
                Weight=("Weight", "mean"),
            )
            .sort_values("SessionDate")
            .reset_index(drop=True)
        )

        return session_summary

    def compute_kpis(self, session_summary: pd.DataFrame) -> dict[str, float]:
        """Compute exercise KPIs from session summary.

        Returns a dict with: latest_1rm, start_1rm, progress (pct change), avg_weight.
        """
        if session_summary.empty:
            return {
                "latest_1rm": 0.0,
                "start_1rm": 0.0,
                "progress": 0.0,
                "avg_weight": 0.0,
            }

        latest_1rm = float(session_summary["Est1RM"].iloc[-1])
        start_1rm = float(session_summary["Est1RM"].iloc[0])
        progress = pct_change(latest_1rm, start_1rm)
        avg_weight = float(session_summary["Weight"].mean())

        return {
            "latest_1rm": round(latest_1rm, 2),
            "start_1rm": round(start_1rm, 2),
            "progress": round(progress, 2),
            "avg_weight": round(avg_weight, 2),
        }

    def compute_history_table(self, df_ex: pd.DataFrame) -> pd.DataFrame:
        """Compute a history table aggregating sets by session date.

        Returns a DataFrame with columns: SessionDate, SeriesCount, TotalReps,
        AvgWeight and Volume.
        """
        df = df_ex.copy()
        df = add_volume_column(df)

        df_summary = (
            df.groupby("SessionDate", as_index=False)
            .agg(
                SeriesCount=("SetNumber", "count"),
                TotalReps=("Repetitions", "sum"),
                AvgWeight=("Weight", "mean"),
                Volume=("Volume", "sum"),
            )
            .sort_values("SessionDate")
            .reset_index(drop=True)
        )

        df_summary["SessionDate"] = pd.to_datetime(df_summary["SessionDate"]).dt.date
        df_summary["AvgWeight"] = df_summary["AvgWeight"].round(1)
        df_summary["Volume"] = df_summary["Volume"].round(1)

        return df_summary
