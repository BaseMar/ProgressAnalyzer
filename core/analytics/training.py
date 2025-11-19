import pandas as pd
from .base import require_columns, add_volume_column, pct_change
from typing import Optional
from .base import compute_est_1rm

class TrainingAnalytics:
    """
    Refaktoryzowana klasa analityczna dla ogólnych miar treningowych.
    Zakłada, że df_sets ma kolumny: SessionDate, Weight, Repetitions, ExerciseName, SetNumber
    """

    def __init__(self, df_sets: pd.DataFrame):
        require_columns(df_sets, ["SessionDate", "Weight", "Repetitions"])
        self.df_sets = df_sets.copy()
        self.df_sets["SessionDate"] = pd.to_datetime(self.df_sets["SessionDate"])
        self.df_sets = add_volume_column(self.df_sets)
        
        # --- obliczenie intensywności na podstawie %1RM ---
        self.df_sets["Est1RM"] = self.df_sets.apply(lambda r: compute_est_1rm(r["Weight"], r["Repetitions"]), axis=1)
        self.df_sets["Intensity"] = self.df_sets["Weight"] / self.df_sets["Est1RM"] * 100

    def weekly_agg_df(self, col: str, agg: str = "mean") -> pd.DataFrame:
        """Zwraca DataFrame z agregacją wg (Year, Week) oraz kolumną Value."""
        df = self.df_sets.copy()
        df["Week"] = df["SessionDate"].dt.isocalendar().week
        df["Year"] = df["SessionDate"].dt.isocalendar().year

        if agg == "mean":
            weekly = df.groupby(["Year", "Week"])[col].mean().reset_index(name="Value")
        elif agg == "sum":
            weekly = df.groupby(["Year", "Week"])[col].sum().reset_index(name="Value")
        else:
            raise ValueError("agg must be 'mean' or 'sum'")

        weekly = weekly.sort_values(["Year", "Week"]).reset_index(drop=True)
        return weekly

    def weekly_agg(self, col: Optional[str] = None, agg_func: str = "mean") -> dict:
        """
        Wrapper: zwraca current/previous/change jak wcześniej, ale oparty o weekly_agg_df.
        Dla sets_per_session: col=None, agg_func='sets_per_session' zostawiamy kompatybilność.
        """
        if agg_func == "sets_per_session":
            df = self.df_sets.copy()
            df["Week"] = df["SessionDate"].dt.isocalendar().week
            df["Year"] = df["SessionDate"].dt.isocalendar().year
            weekly = (
                df.groupby(["Year", "Week"])
                .agg(total_sets=("SetNumber", "count"), total_sessions=("SessionDate", "nunique"))
                .reset_index()
            )
            weekly["Value"] = weekly["total_sets"] / weekly["total_sessions"]
            weekly = weekly.sort_values(["Year", "Week"]).reset_index(drop=True)
        else:
            if col is None:
                raise ValueError("col must be provided unless agg_func == 'sets_per_session'")
            weekly = self.weekly_agg_df(col, agg_func)

        if weekly.empty:
            return {"current": 0.0, "previous": 0.0, "change": 0.0}
        if len(weekly) == 1:
            current = float(weekly.iloc[-1]["Value"])
            return {"current": round(current, 2), "previous": 0.0, "change": 0.0}

        current = float(weekly.iloc[-1]["Value"])
        previous = float(weekly.iloc[-2]["Value"])
        return {
            "current": round(current, 2),
            "previous": round(previous, 2),
            "change": round(pct_change(current, previous), 2),
        }

    def session_count(self) -> int:
        return int(self.df_sets["SessionDate"].dt.date.nunique())
