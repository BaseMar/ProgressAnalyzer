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

from typing import Dict

import pandas as pd
import streamlit as st

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

    def __init__(self, exercises_metrics: Dict) -> None:
        """Initialize with pre-computed exercise metrics.
        
        Args:
            exercises_metrics: Dictionary with 'per_exercise' key containing exercise-level metrics
        """
        self.exercises_metrics = exercises_metrics

    def _build_bodypart_df(self) -> pd.DataFrame:
        """Aggregate exercise metrics per body part.
        
        Returns:
            DataFrame with columns: Body Part, Total_Sets, Total_Volume, Sessions, Avg_1RM
            Sorted by total volume descending.
        """
        per_exercise = self.exercises_metrics.get("per_exercise", {})
        if not per_exercise:
            return pd.DataFrame()

        df = pd.DataFrame(per_exercise).T.dropna(subset=["body_part"])

        return (
            df.groupby("body_part")
            .agg(
                Total_Sets=("total_sets", "sum"),
                Total_Volume=("total_volume", "sum"),
                Sessions=("sessions_count", "sum"),
                Avg_1RM=("estimated_1rm_avg", "mean"),
            )
            .reset_index()
            .rename(columns={"body_part": "Body Part"})
            .sort_values("Total_Volume", ascending=False)
            .reset_index(drop=True)
        )

    def render(self) -> None:
        """Render the complete body parts view."""
        page_title("Body Parts", "Training Distribution")

        body_df = self._build_bodypart_df()

        if body_df.empty:
            st.info("No body part data available.")
            return

        self._render_kpis(body_df)
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
            st.vega_lite_chart(data=data_records, spec=spec, width="stretch")

        with col2:
            chart_label("Avg 1RM per Body Part")
            data_records = body_df.to_dict(orient="records")
            spec2 = _bar_spec(y_field="Avg_1RM", y_title="Avg 1RM (kg)")
            st.vega_lite_chart(data=data_records, spec=spec2, width="stretch")

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
