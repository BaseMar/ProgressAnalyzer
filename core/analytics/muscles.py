from typing import Optional, Tuple

import numpy as np
import pandas as pd

from .base import pct_change


class MuscleAnalytics:
    def __init__(self, df_sets: pd.DataFrame):
        # copy data and normalise timestamps once to avoid repeated conversions
        self.df = df_sets.copy()
        if "SessionDate" in self.df.columns:
            self.df["SessionDate"] = pd.to_datetime(self.df["SessionDate"])
            iso = self.df["SessionDate"].dt.isocalendar()
            self.df["Year"] = iso.year.astype(int)
            self.df["Week"] = iso.week.astype(int)
        self.df["BodyPart"] = (
            self.df.get("BodyPart").fillna("Unknown")
            if "BodyPart" in self.df.columns
            else "Unknown"
        )

        # internal simple cache for computed summary
        self._cached_summary: Optional[pd.DataFrame] = None

        # Only main categories are used
        self.recommended_sessions_map = {
            "Chest": (1, 3),
            "Back": (1, 3),
            "Shoulders": (1, 3),
            "Biceps": (2, 4),
            "Triceps": (2, 4),
            "Legs": (1, 3),
            "Core": (1, 3),
        }
        self.default_recommended = (1, 3)
        self.tolerance_low = 0.9
        self.tolerance_high = 1.1
        self.min_weeks_required = 4
        self.trend_window_weeks = 4
        self.trend_threshold_pct = 5.0

    def _available_weeks(self) -> int:
        """Return number of unique (Year, Week) pairs in the dataset."""
        if self.df.empty:
            return 0
        if "Year" in self.df.columns and "Week" in self.df.columns:
            weeks = self.df.dropna(subset=["Year", "Week"])[
                ["Year", "Week"]
            ].drop_duplicates()
            return len(weeks)
        return 0

    def _weekly_volume_by_bodypart(self) -> pd.DataFrame:
        """Return DataFrame with Year, Week, BodyPart, Volume aggregated per week."""
        # use precomputed Year/Week when available
        df = self.df.copy()
        if "Year" not in df.columns or "Week" not in df.columns:
            # not enough data to build weekly aggregation
            return pd.DataFrame(columns=["Year", "Week", "BodyPart", "WeeklyVolume"])

        weekly = (
            df.groupby(["Year", "Week", "BodyPart"], as_index=False)["Volume"]
            .sum()
            .rename(columns={"Volume": "WeeklyVolume"})
            .sort_values(["Year", "Week"])
            .reset_index(drop=True)
        )
        return weekly

    def muscle_groups_summary(self) -> pd.DataFrame:
        """Return extended summary for each BodyPart with recommended ranges and trends.

        Columns returned:
        - BodyPart, total_volume, mean_intensity, sessions_count, sessions_per_week,
          avg_volume_per_session, recommended_sessions (str), recommended_min, recommended_max,
          load_level, trend_pct, assessment
        """

        if self.df.empty:
            return pd.DataFrame(
                columns=[
                    "BodyPart",
                    "total_volume",
                    "mean_intensity",
                    "sessions_count",
                    "sessions_per_week",
                    "avg_volume_per_session",
                    "recommended_sessions",
                    "recommended_min",
                    "recommended_max",
                    "load_level",
                    "trend_pct",
                    "assessment",
                ]
            )

        # Return cached if available
        if self._cached_summary is not None:
            return self._cached_summary.copy()

        # Base aggregations
        total = self.df.groupby("BodyPart", as_index=False).agg(
            total_volume=("Volume", "sum"), mean_intensity=("Intensity", "mean")
        )

        # Sessions count per bodypart (unique session dates)
        sessions = (
            self.df.groupby("BodyPart")["SessionDate"]
            .nunique()
            .rename("sessions_count")
            .reset_index()
        )

        summary = total.merge(sessions, on="BodyPart", how="left")
        summary["sessions_count"] = summary["sessions_count"].fillna(0).astype(int)

        # Available weeks (compute once)
        weeks = self._available_weeks()
        summary["sessions_per_week"] = summary["sessions_count"].apply(
            lambda c: round(c / weeks, 2) if weeks >= 1 else 0.0
        )

        # Average volume per session
        summary["avg_volume_per_session"] = summary.apply(
            lambda r: round(r["total_volume"] / r["sessions_count"], 1)
            if r["sessions_count"] > 0
            else 0.0,
            axis=1,
        )

        # Recommended ranges
        def _get_recommended(bp: str) -> Tuple[int, int]:
            return self.recommended_sessions_map.get(bp, self.default_recommended)

        summary[["recommended_min", "recommended_max"]] = summary["BodyPart"].apply(
            lambda bp: pd.Series(_get_recommended(bp))
        )

        summary["recommended_sessions"] = summary.apply(
            lambda r: f"{int(r['recommended_min'])}–{int(r['recommended_max'])}", axis=1
        )

        # Load level (compare sessions_per_week to recommended range with tolerance)
        def _load_level(row) -> str:
            spw = row["sessions_per_week"]
            rmin = row["recommended_min"]
            rmax = row["recommended_max"]
            if row["sessions_count"] == 0:
                return "no data"
            if spw < rmin * self.tolerance_low:
                return "too little"
            if spw > rmax * self.tolerance_high:
                return "too much"
            return "OK"

        summary["load_level"] = summary.apply(_load_level, axis=1)

        # Trend calculation: compare last window to previous window of weekly volumes
        weekly = self._weekly_volume_by_bodypart()

        def _calc_trend(bp: str) -> float:
            bp_weekly = weekly[weekly["BodyPart"] == bp].copy()
            if bp_weekly.empty:
                return 0.0
            # compute rolling windows by Year+Week ordering
            bp_weekly = bp_weekly.sort_values(["Year", "Week"]).reset_index(drop=True)
            # get last N weeks and previous N weeks
            n = self.trend_window_weeks
            if (
                len(bp_weekly) < n * 2
                or self._available_weeks() < self.min_weeks_required
            ):
                return 0.0
            last_window = bp_weekly["WeeklyVolume"].iloc[-n:].mean()
            prev_window = bp_weekly["WeeklyVolume"].iloc[-(2 * n) : -n].mean()
            return round(pct_change(last_window, prev_window), 2)

        summary["trend_pct"] = summary["BodyPart"].apply(_calc_trend)

        # Assessment messages
        def _assessment(row) -> str:
            if (
                row["sessions_count"] == 0
                or self._available_weeks() < self.min_weeks_required
            ):
                return "Not enough data to assess."
            trend = row["trend_pct"]
            level = row["load_level"]
            if level == "too little":
                if trend > 0:
                    return "Good direction — volume is increasing. You can continue to increase cautiously."
                return "Increase frequency or training volume for this group."
            if level == "OK":
                if abs(trend) < self.trend_threshold_pct:
                    return "Stable — continue your plan."
                if trend > 0:
                    return "Good — visible progress."
                return "Warning: volume is decreasing — monitor and adjust if needed."
            if level == "too much":
                return "Watch out for overtraining — consider reducing volume/intensity."
            return "No specific assessment."

        summary["assessment"] = summary.apply(_assessment, axis=1)

        # Clean up column order and types
        summary = summary[
            [
                "BodyPart",
                "total_volume",
                "mean_intensity",
                "sessions_count",
                "sessions_per_week",
                "avg_volume_per_session",
                "recommended_sessions",
                "recommended_min",
                "recommended_max",
                "load_level",
                "trend_pct",
                "assessment",
            ]
        ]

        # fill NaNs
        summary["mean_intensity"] = summary["mean_intensity"].fillna(0.0).round(2)
        summary["total_volume"] = summary["total_volume"].fillna(0.0)

        summary = summary.sort_values("BodyPart").reset_index(drop=True)

        # cache and return a copy
        self._cached_summary = summary.copy()
        return summary

    def muscle_kpis(self) -> dict[str, object]:
        """Return high-level KPIs about muscle groups using the extended summary."""
        summary = self.muscle_groups_summary()

        if summary.empty:
            return {
                "most_loaded_bodypart": None,
                "least_loaded_bodypart": None,
                "avg_exercises_per_bodypart": 0.0,
                "avg_intensity": 0.0,
                "intensity_change": 0.0,
                "total_volume": 0.0,
                "volume_change": 0.0,
                "sessions": 0,
                "avg_sets_per_session": 0.0,
                "sets_change": 0.0,
            }

        top = summary.sort_values("total_volume", ascending=False).iloc[0]["BodyPart"]
        least = summary.sort_values("total_volume", ascending=True).iloc[0]["BodyPart"]

        avg_exercises = float(
            self.df.groupby("BodyPart")["ExerciseName"].nunique().mean()
        )
        avg_intensity = (
            float(summary["mean_intensity"].mean())
            if not summary["mean_intensity"].empty
            else 0.0
        )

        total_volume = summary["total_volume"].sum()
        sessions = (
            int(self.df["SessionDate"].nunique())
            if "SessionDate" in self.df.columns
            else 0
        )
        avg_sets_per_session = (
            float(self.df.groupby("SessionDate")["SetNumber"].count().mean())
            if "SetNumber" in self.df.columns
            else 0.0
        )

        return {
            "most_loaded_bodypart": top,
            "least_loaded_bodypart": least,
            "avg_exercises_per_bodypart": round(avg_exercises, 2),
            "avg_intensity": round(avg_intensity, 2),
            "intensity_change": 0.0,
            "total_volume": total_volume,
            "volume_change": 0.0,
            "sessions": sessions,
            "avg_sets_per_session": round(avg_sets_per_session, 2),
            "sets_change": 0.0,
        }

    def filter_dates(self, date_from=None, date_to=None) -> "MuscleAnalytics":
        df = self.df
        if date_from is not None:
            df = df[df["SessionDate"] >= pd.to_datetime(date_from)]
        if date_to is not None:
            df = df[df["SessionDate"] <= pd.to_datetime(date_to)]
        return MuscleAnalytics(df)

    def volume_chart_data(self) -> pd.DataFrame:
        summary = self.muscle_groups_summary()
        df = summary[["BodyPart", "total_volume"]].copy()
        df = df.sort_values("total_volume", ascending=False).reset_index(drop=True)
        return df

    def intensity_chart_data(self) -> pd.DataFrame:
        """Return data for mean intensity chart by body part from the muscle group summary."""
        return self.muscle_groups_summary()[["BodyPart", "mean_intensity"]]
