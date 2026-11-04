"""
Analytics View

Advanced training analytics including fatigue, strength progress, and plan execution.

Responsibilities:
  - Render fatigue and recovery metrics with time-series visualization
  - Display strength progress analysis with top/bottom exercises
  - Compare planned training with recorded sessions
  
All calculations are performed in the metrics layer; this view handles presentation only.
Styling strategy:
  - page_title / section_header / chart_label  → main.css handles rendering
  - st.metric                                  → main.css handles styling
  - Plotly charts                              → themed via PLOTLY_LAYOUT from ui_helpers
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st
from ui.plan_adherence_view import PlanAdherenceView

from ui.utils.ui_helpers import (chart_label, page_title, section_header, ACCENT, DANGER, MUTED, PLOTLY_LAYOUT)


def _apply_theme(fig, title: str = "") -> None:
    """Apply shared Plotly theme to a figure in-place.
    
    Args:
        fig: Plotly Figure object
        title: Optional chart title (rendered in uppercase small-caps)
    """
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=title.upper(), font=dict(color=MUTED, size=10), x=0))


class AnalyticsView:
    """UI view for advanced training analytics.
    
    Displays:
    - Fatigue and recovery monitoring with per-session fatigue scores
    - Strength progress analysis identifying top/bottom improving exercises
    - Plan execution and exercise/set coverage
    
    Data Sources:
    - session_metrics: Per-session and global training metrics
    - exercise_metrics: Exercise-level metrics
    - progress_metrics: Strength progress per exercise
    - fatigue_metrics: Fatigue scores and recovery trends
    """

    def __init__(self, metrics: Dict, *, selected_month=None, exercise_names=None) -> None:
        """Initialize with pre-computed analytics metrics.
        
        Args:
            metrics: Dictionary with keys 'sessions', 'exercises', 'progress', 'fatigue'
        """
        self.session_metrics = metrics.get("sessions", {})
        self.exercise_metrics = metrics.get("exercises", {})
        self.progress_metrics = metrics.get("progress", {})
        self.fatigue_metrics = metrics.get("fatigue", {})
        self.selected_month = selected_month
        self.exercise_names = exercise_names

    def render(self) -> None:
        """Render the complete analytics view."""
        page_title("Analytics", "Training Analytics")
        plan, strength, fatigue = st.tabs(["Plan execution", "Overall strength", "Fatigue"])
        with plan:
            PlanAdherenceView(selected_month=self.selected_month, exercise_names=self.exercise_names).render()
        with strength:
            self._progress_section()
        with fatigue:
            self._fatigue_section()

    def _fatigue_section(self) -> None:
        """Render fatigue and recovery insights with per-session fatigue trends."""
        section_header("Fatigue & Recovery")

        per_session = self.fatigue_metrics.get("per_session", {})
        global_f = self.fatigue_metrics.get("global", {})

        if not per_session:
            st.info("No fatigue data.")
            return

        total_sets = sum(s["total_sets"] for s in self.session_metrics.get("per_session", {}).values())
        failure_sets = sum(s["sets_to_failure"] for s in self.session_metrics.get("per_session", {}).values())
        failure_pct = (failure_sets / total_sets * 100) if total_sets else 0
        avg_1rm = self.session_metrics.get("global", {}).get("avg_estimated_1rm")

        cols = st.columns(5)
        cols[0].metric("Avg Fatigue Score", global_f.get("avg_fatigue_score", "—"))
        ratio = global_f.get("high_fatigue_sessions_ratio")
        cols[1].metric("High-score sessions", f"{ratio * 100:.1f}%" if ratio is not None else "—")
        cols[2].metric("Longest high-score run", global_f.get("max_consecutive_high_fatigue_sessions", "—"))
        cols[3].metric("Mean session e1RM", f"{avg_1rm:.1f} kg" if avg_1rm is not None else "—", help="Average of session mean estimated 1RM values. This is not relative intensity.")
        cols[4].metric("Sets to Failure", f"{round(failure_pct, 1)}%")

        df = pd.DataFrame([
            {"date": s.get("session_timestamp", s.get("session_date")), "fatigue_score": s.get("fatigue_score", 0), "session_id": sid}
            for sid, s in per_session.items()
        ]).dropna(subset=["date"])

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            fig = px.line(
                df, x="date", y="fatigue_score",
                markers=True,
                labels={"date": "Date", "fatigue_score": "Fatigue Score"},
                hover_data=["session_id"],
            )
            fig.update_traces(
                line_color=ACCENT,
                line_width=2,
                marker=dict(color=ACCENT, size=5),
            )
            _apply_theme(fig)

            chart_label("Fatigue Score")
            fig.update_yaxes(range=[0, 1])
            st.plotly_chart(fig, width='stretch')

        st.caption("Fatigue Score is an unvalidated 0–1 heuristic based on RIR, failure sets, volume and timed work. High score means ≥0.7; it does not measure physiological fatigue or recovery. Inferred and explicit warm-ups are excluded; unknown effort remains in descriptive workload.")

    def _progress_section(self) -> None:
        """Render strength progress analysis with top/bottom improving exercises."""
        section_header("Strength Progress")
        st.caption(
            "Compares the first and last windows of up to 3 sessions in the selected period, "
            "using the best estimated 1RM per session (longest set for timed exercises). "
            "At least 2 comparable sessions are required."
        )
        st.caption("Ordinary progress uses eligible working sets; light work, missing effort and planned deloads are excluded. Timed progress uses duration without requiring RIR.")

        per_ex = self.progress_metrics.get("per_exercise", {})
        if not per_ex:
            st.info("No progress data.")
            return

        df = pd.DataFrame(per_ex).T
        df["progress_per_exposure"] = df["progress_pct"] / df["exposure_count"]
        df.fillna(0, inplace=True)

        median_progress = df["progress_pct"].median()
        improving = (df["progress_pct"] > 2).sum()
        progress_ratio = improving / len(df) * 100 if len(df) else 0
        top_exercise = df.loc[df["progress_pct"].idxmax(), "exercise_name"]
        worst_exercise = df.loc[df["progress_pct"].idxmin(), "exercise_name"]

        cols = st.columns(4)
        cols[0].metric("Median Progress", f"{round(median_progress, 1)}%")
        cols[1].metric("Progress Ratio", f"{round(progress_ratio)}%")
        cols[2].metric("Highest change", top_exercise)
        cols[3].metric("Lowest change", worst_exercise)

        top10 = df.sort_values("progress_pct", ascending=False).head(10)
        bottom10 = df.sort_values("progress_pct", ascending=True).head(10)

        col1, col2 = st.columns(2)

        with col1:
            chart_label("Top Strength Progress")
            fig_top = px.bar(
                top10, x="exercise_name", y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "Exercise", "progress_pct": "Progress (%)"},
            )
            fig_top.update_traces(
                marker_color=ACCENT,
                marker_opacity=0.85,
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont=dict(color=MUTED, size=10),
            )
            fig_top.update_layout(bargap=0.35)
            _apply_theme(fig_top)
            st.plotly_chart(fig_top, width='stretch')

        with col2:
            chart_label("Weakest Strength Progress")
            fig_bottom = px.bar(
                bottom10, x="exercise_name", y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "Exercise", "progress_pct": "Progress (%)"},
            )
            fig_bottom.update_traces(
                marker_color=DANGER,
                marker_opacity=0.85,
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont=dict(color=MUTED, size=10),
            )
            fig_bottom.update_layout(bargap=0.35)
            _apply_theme(fig_bottom)
            st.plotly_chart(fig_bottom, width='stretch')
