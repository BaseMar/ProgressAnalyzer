"""
Analytics view for the UI layer.

Styling strategy (mirrors dashboard_view.py):
  - page_title / section_header / chart_label  → main.css handles rendering
  - st.metric                                  → main.css handles styling
  - Plotly charts                              → themed via PLOTLY_LAYOUT from ui_helpers
  - Plateau expanders                          → main.css stExpander styles apply
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.utils.ui_helpers import (chart_label, fmt_num, page_title, section_header, ACCENT, DANGER, MUTED, WARN, PLOTLY_LAYOUT)

def _apply_theme(fig, title: str = "") -> None:
    """Apply the shared Plotly theme to a figure in-place."""
    fig.update_layout(**PLOTLY_LAYOUT,title=dict(text=title.upper(), font=dict(color=MUTED, size=10), x=0))


class AnalyticsView:
    def __init__(self, metrics: Dict) -> None:
        self.session_metrics = metrics.get("sessions", {})
        self.exercise_metrics = metrics.get("exercises", {})
        self.progress_metrics = metrics.get("progress", {})
        self.fatigue_metrics = metrics.get("fatigue", {})

    def render(self) -> None:
        page_title("Analytics", "Training Analytics")
        self._fatigue_section()
        self._progress_section()

    def _fatigue_section(self) -> None:
        section_header("Fatigue & Recovery")

        per_session = self.fatigue_metrics.get("per_session", {})
        global_f = self.fatigue_metrics.get("global", {})

        if not per_session:
            st.info("No fatigue data.")
            return

        total_sets = sum(s["total_sets"] for s in self.session_metrics.get("per_session", {}).values())
        failure_sets = sum(s["sets_to_failure"] for s in self.session_metrics.get("per_session", {}).values())
        failure_pct = (failure_sets / total_sets * 100) if total_sets else 0
        avg_intensity = self.session_metrics.get("global", {}).get("avg_intensity", 0)

        cols = st.columns(5)
        cols[0].metric("Avg Fatigue Score", global_f.get("avg_fatigue_score", "—"))
        cols[1].metric("High Fatigue Sessions", global_f.get("high_fatigue_sessions_ratio", "—"))
        cols[2].metric("Max Consecutive High Fatigue", global_f.get("max_consecutive_high_fatigue_sessions", "—"))
        cols[3].metric("Avg Session Intensity", f"{round(avg_intensity, 2)}%")
        cols[4].metric("Sets to Failure", f"{round(failure_pct, 1)}%")

        df = pd.DataFrame([
            {"date": s.get("session_date"), "fatigue_score": s.get("fatigue_score", 0)}
            for s in per_session.values()
        ]).dropna(subset=["date"])

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")

            fig = px.line(
                df, x="date", y="fatigue_score",
                markers=True,
                labels={"date": "Session Date", "fatigue_score": "Fatigue Score"},
            )
            fig.update_traces(
                line_color=ACCENT,
                line_width=2,
                marker=dict(color=ACCENT, size=5),
            )
            _apply_theme(fig)

            chart_label("Fatigue Score Over Time")
            st.plotly_chart(fig, width='stretch')

        ratio = global_f.get("high_fatigue_sessions_ratio", 0)
        if ratio > 0.3:
            st.warning("High frequency of fatigue-heavy sessions — monitor recovery.")
        else:
            st.success("Fatigue levels are balanced. Keep up the consistency.")

    def _progress_section(self) -> None:
        section_header("Strength Progress")

        per_ex = self.progress_metrics.get("per_exercise", {})
        if not per_ex:
            st.info("No progress data.")
            return

        df = pd.DataFrame(per_ex).T
        df["progress_per_exposure"] = df["progress_pct"] / df["exposure_count"]
        df.fillna(0, inplace=True)

        median_progress = df["progress_pct"].median()
        improving = (df["progress_pct"] > 2).sum()
        plateau_count = (df["progress_pct"].abs() < 2).sum()
        progress_ratio = improving / len(df) * 100 if len(df) else 0
        top_exercise = df.loc[df["progress_pct"].idxmax(), "exercise_name"]
        worst_exercise = df.loc[df["progress_pct"].idxmin(), "exercise_name"]

        cols = st.columns(5)
        cols[0].metric("Median Progress", f"{round(median_progress, 1)}%")
        cols[1].metric("Progress Ratio", f"{round(progress_ratio)}%")
        cols[2].metric("Plateaus", int(plateau_count))
        cols[3].metric("Top Improver", top_exercise)
        cols[4].metric("Top Regressor", worst_exercise)

        top10 = df.sort_values("progress_pct", ascending=False).head(10)
        bottom10 = df.sort_values("progress_pct", ascending=True).head(10)

        col1, col2 = st.columns(2)

        with col1:
            chart_label("Top 10 Exercises")
            fig_top = px.bar(
                top10, x="exercise_name", y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "", "progress_pct": "Progress (%)"},
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
            chart_label("Bottom 10 Exercises")
            fig_bottom = px.bar(
                bottom10, x="exercise_name", y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "", "progress_pct": "Progress (%)"},
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

        self._plateau_section(per_ex)

    def _plateau_section(self, per_ex: dict) -> None:
        section_header("Plateau Zone Analysis")

        exercise_per = self.exercise_metrics.get("per_exercise", {})
        today = datetime.now().date()
        recency_threshold = 28

        plateau_data = []
        abandoned_data = []

        for ex_id, row in per_ex.items():
            if abs(row["progress_pct"]) >= 2:
                continue

            ex_info = exercise_per.get(ex_id, {})
            per_session_1rm = ex_info.get("per_session_1rm", [])
            last_date = pd.to_datetime(per_session_1rm[-1]["date"]).date() if per_session_1rm else None

            if last_date is None:
                continue

            days_since = (today - last_date).days
            entry = {
                "exercise_name": row["exercise_name"],
                "progress_pct": row["progress_pct"],
                "exposure_count": row["exposure_count"],
                "last_date":     last_date,
                "days_since":    days_since,
            }

            if days_since <= recency_threshold:
                plateau_data.append(entry)
            else:
                abandoned_data.append(entry)

        plateau_data = sorted(plateau_data,   key=lambda x: x["exposure_count"], reverse=True)
        abandoned_data = sorted(abandoned_data, key=lambda x: x["days_since"], reverse=True)

        if not plateau_data:
            st.success("No active exercises in plateau zone — all recently trained exercises are progressing.")
        else:
            st.info(f"{len(plateau_data)} active exercise(s) stuck in plateau (trained in last {recency_threshold} days)")

            for i, item in enumerate(plateau_data):
                recs = []
                if item["exposure_count"] < 5:
                    recs.append("**Increase Frequency** — Less than 5 sessions; aim for 2–3×/week for a stronger adaptation signal.")
                elif item["exposure_count"] >= 12:
                    recs.append("**Boost Volume or Intensity** — 12+ exposures; try +10% weight, change rep range, or add drop sets.")
                else:
                    recs.append("**Change Stimulus** — Try a new angle, tempo (3-0-1), pause reps, or a variation.")

                if item["progress_pct"] < -0.5:
                    recs.append("**Form Check** — Slight regression detected; review technique or consider a deload week.")
                else:
                    recs.append("**Stabilising** — Minor fluctuations; maintain current approach or progress incrementally.")

                label = (
                    f"{item['exercise_name']}   ·   "
                    f"Progress: {item['progress_pct']:.1f}%   ·   "
                    f"Exposures: {int(item['exposure_count'])}   ·   "
                    f"Last: {item['days_since']}d ago"
                )
                with st.expander(label, expanded=(i == 0)):
                    for rec in recs:
                        st.markdown(f"— {rec}")

        if abandoned_data:
            section_header("Abandoned Exercises")
            for item in abandoned_data:
                st.markdown(
                    f"**{item['exercise_name']}** — "
                    f"Progress: {item['progress_pct']:.1f}% · "
                    f"Last trained: {item['days_since']} days ago"
                )
