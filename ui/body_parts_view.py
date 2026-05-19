"""
Body Parts View

Displays training distribution and performance metrics aggregated by body part.

Responsibilities:
  - Render body part overview KPIs (count, most/least trained, avg volume)
  - Display volume and strength distribution across body parts
  - Provide comparative table of body parts ranked by volume
  
All metrics are pre-computed in the exercise_metrics layer; this view aggregates and presents them.
"""

from __future__ import annotations

from collections import defaultdict
from calendar import monthrange
from typing import Dict

import pandas as pd
import streamlit as st

from ui.utils.body_heatmap import render_body_heatmap
from ui.utils.body_parts_table import render_body_parts_table
from ui.utils.ui_helpers import ACCENT, VEGA_CONFIG, chart_label, format_number, page_title, section_header


class BodyPartsView:
    """UI view for body-part-level training distribution analysis.
    
    Aggregates exercise metrics by body part to show:
    - Most and least trained body parts
    - Volume distribution across body parts
    - Average strength (1RM) per body part
    - Training balance overview
    
    Data Source:
    - exercises_metrics: Pre-computed per-exercise metrics aggregated by body part
    """

    def __init__(self, exercises_metrics: Dict, selected_month: str | None = None) -> None:
        """Initialize with pre-computed exercise metrics.
        
        Args:
            exercises_metrics: Dictionary with 'per_exercise' key containing exercise-level metrics
            selected_month: Active global month filter, or "All time".
        """
        self.exercises_metrics = exercises_metrics
        self.selected_month = selected_month

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
                rows.append(
                    {
                        "Body Part": str(body_part),
                        "Total_Sets": float(row["total_sets"]) * factor,
                        "Total_Volume": float(row["total_volume"]) * factor,
                        "Avg_1RM": row.get("estimated_1rm_avg"),
                        "Weight": max(float(row["total_sets"]) * factor, 0.0),
                    }
                )

            for point in row.get("per_session_1rm", []):
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
            for point in row.get("per_session_1rm", []):
                date = point.get("date")
                if date is not None:
                    dates.append(pd.to_datetime(date).normalize())
        return dates

    def render(self) -> None:
        """Render the complete body parts view."""
        page_title("Body Parts", "Training Distribution")

        body_df = self._build_bodypart_df()

        if body_df.empty:
            st.info("No body part data available.")
            return

        self._render_kpis(body_df)
        self._render_heatmap(body_df)
        self._render_charts(body_df)
        self._render_table(body_df)

    def _render_kpis(self, body_df: pd.DataFrame) -> None:
        """Render body part overview metrics."""
        section_header("Overview")

        cols = st.columns(4)
        cols[0].metric("Body Parts Trained", len(body_df))
        cols[1].metric("Most Trained", body_df.iloc[0]["Body Part"].title())
        cols[2].metric("Least Trained", body_df.iloc[-1]["Body Part"].title())
        cols[3].metric("Avg Volume / Part", f"{format_number(body_df['Total_Volume'].mean(), 0)} kg")

    def _render_charts(self, body_df: pd.DataFrame) -> None:
        """Render volume and strength distribution charts."""
        section_header("Training Distribution")

        col1, col2 = st.columns(2)

        with col1:
            chart_label("Volume per Body Part")
            data_records = body_df.to_dict(orient="records")
            spec = _bar_spec(y_field="Total_Volume", y_title="Volume (kg)")
            st.vega_lite_chart(
                data=data_records,
                spec=spec,
                width="stretch",
                key=f"body_parts_volume_{_data_signature(body_df, 'Total_Volume')}",
            )

        with col2:
            chart_label("Avg 1RM per Body Part")
            data_records = body_df.to_dict(orient="records")
            spec2 = _bar_spec(y_field="Avg_1RM", y_title="Avg 1RM (kg)")
            st.vega_lite_chart(
                data=data_records,
                spec=spec2,
                width="stretch",
                key=f"body_parts_1rm_{_data_signature(body_df, 'Avg_1RM')}",
            )

    def _render_heatmap(self, body_df: pd.DataFrame) -> None:
        """Render training target heatmap for the active filter period."""
        section_header("Training Heatmap")
        period_weeks, period_label = self._training_period()
        render_body_heatmap(body_df, period_weeks, period_label)

    def _render_table(self, body_df: pd.DataFrame) -> None:
        """Render detailed body part comparison table."""
        section_header("Body Part Comparison")
        render_body_parts_table(body_df)


def _bar_spec(y_field: str, y_title: str) -> dict:
    """Generate themed horizontal bar chart spec.
    
    Horizontal layout presents categorical body-part labels better than vertical bars.
    Uses AccentColor from the design tokens and responsive sizing.
    
    Args:
        y_field: Column name for the y-axis (e.g., 'Total_Volume')
        y_title: Display title for the x-axis (e.g., 'Volume (kg)')
    
    Returns:
        Vega-Lite specification dictionary for st.vega_lite_chart()
    """
    return {
        "config": VEGA_CONFIG,
        "width": "container",
        "height": 280,
        "mark": {
            "type": "bar",
            "color": ACCENT,
            "opacity": 0.85,
            "cornerRadiusEnd": 3,
        },
        "encoding": {
            "y": {
                "field": "Body Part",
                "type": "nominal",
                "sort": "-x",
                "axis": {"labelFontSize": 11},
                "title": None,
            },
            "x": {
                "field": y_field,
                "type": "quantitative",
                "axis": {"tickCount": 5},
                "title": y_title,
            },
            "tooltip": [
                {"field": "Body Part", "type": "nominal"},
                {
                    "field": y_field,
                    "type": "quantitative",
                    "title": y_title,
                    "format": ".0f",
                },
            ],
        },
    }


def _data_signature(df: pd.DataFrame, value_col: str) -> int:
    chart_df = df[["Body Part", value_col]].copy()
    return int(pd.util.hash_pandas_object(chart_df, index=True).sum())
