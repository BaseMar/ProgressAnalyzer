"""Muscle allocation, automatic weekly targets and logged training distribution."""

from __future__ import annotations

from collections import defaultdict
from calendar import monthrange
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.utils.body_heatmap import render_body_heatmap
from ui.utils.body_parts_table import render_body_parts_table
from ui.utils.ui_helpers import ACCENT, PLOTLY_LAYOUT, section_header


class BodyPartsView:
    """Aggregate exercise metrics for the Muscle distribution analysis."""

    def __init__(self, exercises_metrics: Dict, selected_month: str | None = None, *, weekly_targets=None) -> None:
        """Initialize with pre-computed exercise metrics.
        
        Args:
            exercises_metrics: Dictionary with 'per_exercise' key containing exercise-level metrics
            selected_month: Active global month filter, or "All time".
        """
        self.exercises_metrics = exercises_metrics
        self.selected_month = selected_month
        self.weekly_targets = weekly_targets

    def _build_bodypart_df(self) -> pd.DataFrame:
        """Aggregate exercise metrics per body part.
        
        Returns:
            DataFrame with columns: Body Part, Total_Sets, Total_Volume, Sessions, Avg_1RM
            Sorted by total volume descending.
        """
        per_exercise = self.exercises_metrics.get("per_exercise", {})
        if not per_exercise:
            return pd.DataFrame()

        rows = []
        session_dates_by_part: dict[str, set] = defaultdict(set)

        for row in per_exercise.values():
            muscle_targets = row.get("muscle_targets") or []
            if not muscle_targets and row.get("body_part"):
                muscle_targets = [
                    {
                        "muscle_group": row["body_part"],
                        "muscle_name": row["body_part"],
                        "role": "primary",
                        "set_factor": 1.0,
                    }
                ]

            for target in muscle_targets:
                body_part = target.get("muscle_group")
                if not body_part:
                    continue
                factor = float(target.get("set_factor", 1.0))
                set_exposure = float(row["total_sets"])
                rows.append(
                    {
                        "Body Part": str(body_part),
                        "Total_Sets": set_exposure * factor,
                        "Total_Volume": float(row["total_volume"]) * factor,
                        "Avg_1RM": row.get("estimated_1rm_avg"),
                        "Weight": max(set_exposure * factor, 0.0),
                    }
                )

            session_points = [
                *row.get("per_session_volume", row.get("per_session_1rm", [])),
                *row.get("per_session_duration", []),
            ]
            for point in session_points:
                date = point.get("date")
                if date is not None:
                    for target in muscle_targets:
                        body_part = target.get("muscle_group")
                        if body_part:
                            session_dates_by_part[str(body_part)].add(pd.to_datetime(date).date())

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        weighted_1rm = (
            df.dropna(subset=["Avg_1RM"])
            .assign(Weighted_1RM=lambda x: x["Avg_1RM"] * x["Weight"])
            .groupby("Body Part", dropna=True)
            .agg(Weighted_1RM=("Weighted_1RM", "sum"), Weight=("Weight", "sum"))
        )

        body_df = (
            df.groupby("Body Part", dropna=True)
            .agg(
                Total_Sets=("Total_Sets", "sum"),
                Total_Volume=("Total_Volume", "sum"),
                Avg_1RM=("Avg_1RM", "mean"),
            )
            .reset_index()
        )
        if not weighted_1rm.empty:
            body_df = body_df.drop(columns=["Avg_1RM"]).merge(
                weighted_1rm.reset_index(),
                on="Body Part",
                how="left",
            )
            body_df["Avg_1RM"] = body_df.apply(
                lambda row: row["Weighted_1RM"] / row["Weight"] if row["Weight"] else None,
                axis=1,
            )
            body_df = body_df.drop(columns=["Weighted_1RM", "Weight"])

        body_df["Sessions"] = body_df["Body Part"].map(
            lambda part: len(session_dates_by_part.get(str(part), set()))
        )

        return (
            body_df.sort_values("Total_Volume", ascending=False)
            .reset_index(drop=True)
        )

    def _training_period(self) -> tuple[float, str]:
        """Return the filtered period length in weeks and a display label."""
        selected_month = self.selected_month
        if selected_month and selected_month != "All time":
            year, month = map(int, selected_month.split("-"))
            days_in_month = monthrange(year, month)[1]
            start = pd.Timestamp(year=year, month=month, day=1)
            end = pd.Timestamp(year=year, month=month, day=days_in_month)
            today = pd.Timestamp.today().normalize()

            if today.year == year and today.month == month:
                end = min(end, today)

            days = max((end - start).days + 1, 1)
            return max(days / 7, 1.0), selected_month

        dates = self._metric_dates()
        if not dates:
            return 1.0, "All time"

        start = min(dates)
        end = max(dates)
        days = max((end - start).days + 1, 1)
        return max(days / 7, 1.0), f"All time ({start:%Y-%m-%d} - {end:%Y-%m-%d})"

    def _metric_dates(self) -> list[pd.Timestamp]:
        dates = []
        for row in self.exercises_metrics.get("per_exercise", {}).values():
            for point in row.get("per_session_volume", row.get("per_session_1rm", [])):
                date = point.get("date")
                if date is not None:
                    dates.append(pd.to_datetime(date).normalize())
        return dates

    def render(self) -> None:
        """Render muscle allocation within Analysis."""
        body_df = self._build_bodypart_df()
        if body_df.empty:
            st.info("No body part data available.")
            body_df = pd.DataFrame(columns=["Body Part", "Total_Sets", "Total_Volume", "Sessions", "Avg_1RM"])
        measure = st.radio("Distribution view", ["Muscle map", "Set allocation"], horizontal=True, key="analysis_muscle_view")
        st.caption("Muscle exposure is an allocation estimate: sets are weighted by each exercise's saved muscle targets. This does not measure muscle growth or physiological fatigue.")
        if measure == "Muscle map":
            self._render_heatmap(body_df)
        elif body_df.empty:
            st.info("Log a workout to see set allocation.")
        else:
            st.plotly_chart(_bar_fig(body_df, "Total_Sets", "Allocated set equivalents"), width="stretch", key="analysis_muscle_sets")
        if not body_df.empty:
            with st.expander("Allocation details"):
                self._render_table(body_df)

    def _render_heatmap(self, body_df: pd.DataFrame) -> None:
        """Render training target heatmap for the active filter period."""
        section_header("Training Heatmap")
        period_weeks, period_label = self._training_period()
        render_body_heatmap(body_df, period_weeks, period_label, weekly_targets=self.weekly_targets)

    def _render_table(self, body_df: pd.DataFrame) -> None:
        """Render detailed body part comparison table."""
        section_header("Body Part Comparison")
        render_body_parts_table(body_df)


def _bar_fig(body_df: pd.DataFrame, y_field: str, y_title: str):
    chart_df = body_df.sort_values(y_field, ascending=False).copy()
    fig = px.bar(
        chart_df,
        x=y_field,
        y="Body Part",
        orientation="h",
        custom_data=["Total_Sets", "Total_Volume", "Sessions", "Avg_1RM"],
    )
    fig.update_traces(
        marker_color=ACCENT,
        opacity=0.85,
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"{y_title}: " + "%{x:,.0f}<br>"
            "Sets: %{customdata[0]:,.1f}<br>"
            "Volume: %{customdata[1]:,.0f} kg<br>"
            "Sessions: %{customdata[2]:.0f}<br>"
            "Avg 1RM: %{customdata[3]:,.1f} kg"
            "<extra></extra>"
        ),
    )
    layout = {
        **PLOTLY_LAYOUT,
        "height": 320,
        "margin": dict(l=8, r=8, t=8, b=8),
        "xaxis_title": y_title,
        "yaxis_title": None,
        "bargap": 0.28,
    }
    fig.update_layout(**layout)
    fig.update_yaxes(autorange="reversed")
    return fig
