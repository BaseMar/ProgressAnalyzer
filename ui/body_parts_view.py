"""Muscle allocation, automatic weekly targets and logged training distribution."""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from metrics.muscle_volume import allocation_components
from ui.utils.body_heatmap import render_body_heatmap
from ui.utils.muscle_distribution_table import render_weekly_distribution
from ui.utils.ui_helpers import ACCENT, PLOTLY_LAYOUT


class BodyPartsView:
    """Aggregate exercise metrics for the Muscle distribution analysis."""

    def __init__(
        self, exercises_metrics: Dict, selected_month: str | None = None, *, weekly_targets=None
    ) -> None:
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
            DataFrame with columns: Body Part, Total_Sets, Total_Volume, Sessions
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
                if not body_part or not str(body_part).strip():
                    continue
                factor = float(target.get("set_factor", 1.0))
                set_exposure = float(row.get("dynamic_sets", row["total_sets"]))
                rows.append(
                    {
                        "Body Part": str(body_part).strip().title(),
                        **allocation_components(set_exposure, target),
                        "Timed_Sets": float(row.get("timed_sets", 0)) * factor,
                        "Total_Volume": float(row["total_volume"]) * factor,
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
                        if body_part and str(body_part).strip():
                            session_dates_by_part[str(body_part).strip().title()].add(
                                pd.to_datetime(date).date()
                            )

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        body_df = (
            df.groupby("Body Part", dropna=True)
            .agg(
                Total_Sets=("Total_Sets", "sum"),
                Direct_Sets=("Direct_Sets", "sum"),
                Indirect_Sets=("Indirect_Sets", "sum"),
                Stabilizer_Sets=("Stabilizer_Sets", "sum"),
                Unclassified_Sets=("Unclassified_Sets", "sum"),
                Timed_Sets=("Timed_Sets", "sum"),
                Total_Volume=("Total_Volume", "sum"),
            )
            .reset_index()
        )
        body_df["Sessions"] = body_df["Body Part"].map(
            lambda part: len(session_dates_by_part.get(str(part), set()))
        )

        return body_df.sort_values("Total_Volume", ascending=False).reset_index(drop=True)

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
            body_df = pd.DataFrame(columns=["Body Part", "Total_Sets", "Total_Volume", "Sessions"])
        measure = st.radio(
            "Distribution view",
            ["Muscle map", "Set allocation"],
            horizontal=True,
            key="analysis_muscle_view",
        )
        period_weeks, period_label = self._training_period()
        summary = render_weekly_distribution(
            body_df, period_weeks, period_label, weekly_targets=self.weekly_targets
        )
        if "Timed_Sets" in body_df and body_df["Timed_Sets"].gt(0).any():
            with st.expander("Timed sets"):
                st.dataframe(
                    body_df.loc[body_df["Timed_Sets"] > 0, ["Body Part", "Timed_Sets"]].rename(
                        columns={"Timed_Sets": "Allocated timed sets"}
                    ),
                    hide_index=True,
                    width="stretch",
                )
        if measure == "Muscle map":
            render_body_heatmap(summary, period_weeks, period_label)
        elif body_df.empty:
            st.info("Log a workout to see set allocation.")
        else:
            st.plotly_chart(
                _bar_fig(body_df, "Total_Sets", "Sets in selected period"),
                width="stretch",
                key="analysis_muscle_sets",
            )


def _bar_fig(body_df: pd.DataFrame, y_field: str, y_title: str):
    chart_df = body_df.sort_values(y_field, ascending=False).copy()
    fig = px.bar(
        chart_df,
        x=y_field,
        y="Body Part",
        orientation="h",
    )
    fig.update_traces(
        marker_color=ACCENT,
        opacity=0.85,
        hovertemplate=(f"<b>%{{y}}</b><br>{y_title}: " + "%{x:,.0f}<br><extra></extra>"),
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
