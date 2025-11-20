# core/analytics/training.py
import pandas as pd
from typing import Optional
from .base import require_columns, add_volume_column, pct_change, compute_est_1rm

class TrainingAnalytics:
    REQUIRED_COLS = ["SessionDate", "Weight", "Repetitions", "ExerciseName", "SetNumber"]

    def __init__(self, df_sets: pd.DataFrame):
        require_columns(df_sets, ["SessionDate", "Weight", "Repetitions"])

        self.df_sets = df_sets.copy()
        self.df_sets["SessionDate"] = pd.to_datetime(self.df_sets["SessionDate"])
        self.df_sets = add_volume_column(self.df_sets)
        
        reps = self.df_sets["Repetitions"].astype(float)
        weight = self.df_sets["Weight"].astype(float)
        
        self.df_sets["Est1RM"] = compute_est_1rm(weight, reps)
        mask_0 = self.df_sets["Est1RM"] == 0
        self.df_sets.loc[mask_0, "Est1RM"] = self.df_sets.loc[mask_0, "Weight"]
        
        self.df_sets["Intensity"] = (self.df_sets["Weight"] / self.df_sets["Est1RM"]) * 100.0

        iso = self.df_sets["SessionDate"].dt.isocalendar()
        self.df_sets["Week"] = iso.week.astype(int)
        self.df_sets["Year"] = iso.year.astype(int)

        if "BodyPart" not in self.df_sets.columns:
            self.df_sets["BodyPart"] = None

    def weekly_agg_df(self, col: str, agg: str = "mean") -> pd.DataFrame:
        """Zwraca DataFrame z agregacją wg (Year, Week) oraz kolumną Value.Jeśli kolumna nie istnieje, tworzymy ją jako 0.0 (bez łamania starzejącego się UI)."""
        df = self.df_sets

        if col not in df.columns:
            df = df.copy()
            df[col] = 0.0

        if agg == "mean":
            weekly = df.groupby(["Year", "Week"], as_index=False)[col].mean().rename(columns={col: "Value"})
        elif agg == "sum":
            weekly = df.groupby(["Year", "Week"], as_index=False)[col].sum().rename(columns={col: "Value"})
        else:
            raise ValueError("agg must be 'mean' or 'sum'")

        weekly = weekly.sort_values(["Year", "Week"]).reset_index(drop=True)
        return weekly

    def weekly_agg(self, col: Optional[str] = None, agg_func: str = "mean") -> dict:
        """Wrapper: zwraca current/previous/change.Dla sets_per_session: col=None, agg_func='sets_per_session' - kompatybilność zachowana.
"""
        if agg_func == "sets_per_session":
            df = self.df_sets
            weekly = (df.groupby(["Year", "Week"], as_index=False).agg(total_sets=("SetNumber", "count"), total_sessions=("SessionDate", "nunique")))
            weekly["Value"] = weekly["total_sets"] / weekly["total_sessions"].replace(0, 1)
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

    def muscle_groups_summary(self) -> pd.DataFrame:
        """Agreguje dane po BodyPart:
            - total_volume: suma Volume (kg * reps)
            - mean_intensity: średnia Intensity (%1RM)
        Zwraca df z kolumnami: BodyPart, total_volume, mean_intensity"""
        
        df = self.df_sets.copy()
        
        df["BodyPart"] = df["BodyPart"].fillna("Unknown")
        summary = (df.groupby("BodyPart", as_index=False).agg(total_volume=("Volume", "sum"), mean_intensity=("Intensity", "mean")).sort_values("BodyPart").reset_index(drop=True)
        )

        summary["mean_intensity"] = summary["mean_intensity"].fillna(0.0)
        summary["total_volume"] = summary["total_volume"].fillna(0.0)

        return summary
