"""
Analytics view for the UI layer.

High-level training analytics:
- consistency
- progress
- intensity
- balance
"""

from typing import Dict
import pandas as pd
import streamlit as st


class AnalyticsView:
    """
    High-level analytics dashboard.

    Data sources:
    - session metrics
    - exercise metrics
    """

    def __init__(self, metrics: Dict):
        self.session_metrics = metrics.get("sessions", {})
        self.exercise_metrics = metrics.get("exercises", {})

    def render(self) -> None:
        st.header("Analytics")

        self._consistency_section()
        st.divider()

        self._progress_section()
        st.divider()

        self._intensity_section()
        st.divider()

        self._balance_section()

    def _consistency_section(self):
        st.subheader("Consistency")

        per_session = self.session_metrics.get("per_session", {})
        global_m = self.session_metrics.get("global", {})

        if not per_session:
            st.info("No session data.")
            return

        # --- KPIs ---
        c1, c2, c3 = st.columns(3)

        c1.metric("Sessions / Week", round(global_m.get("avg_sessions_per_week", 0), 2))
        
        dur = global_m.get("avg_session_duration")
        c2.metric("Avg Duration (min)", round(dur, 1) if dur else "—")

        sets = global_m.get("avg_sets_per_session")
        c3.metric("Avg Sets / Session", round(sets, 1) if sets else "—",)

        rows = []
        for s in per_session.values():
            if not s.get("session_date"):
                continue

            d = pd.to_datetime(s["session_date"])
            iso = d.isocalendar()
            rows.append({"year": iso.year, "week": iso.week})

        if rows:
            df = (pd.DataFrame(rows).value_counts().reset_index(name="sessions").sort_values(["year", "week"]))
            df["year_week"] = (df["year"].astype(str) + "-W" + df["week"].astype(str))
            st.line_chart(df.set_index("year_week")["sessions"], height=250)

    def _progress_section(self):
        st.subheader("Progress")

        per_ex = self.exercise_metrics.get("per_exercise", {})

        if not per_ex:
            st.info("No exercise data.")
            return

        df = pd.DataFrame(per_ex).T

        # --- KPIs ---
        best_strength = df.loc[df["strength_trend_1rm"].idxmax()]
        best_volume = df.loc[df["volume_trend"].idxmax()]

        c1, c2 = st.columns(2)

        c1.metric("Top Strength Gain", best_strength["exercise_name"], delta=round(best_strength["strength_trend_1rm"]))
        c2.metric("Top Volume Gain", best_volume["exercise_name"], delta=int(best_volume["volume_trend"]))

        per_session = self.session_metrics.get("per_session", {})

        rows = []
        for s in per_session.values():
            if s.get("session_date"):
                rows.append({"date": s["session_date"], "volume": s["total_volume"]})

        if rows:
            vol_df = (pd.DataFrame(rows).sort_values("date").set_index("date"))
                      
            st.markdown("**Total Volume Over Time**")
            st.line_chart(vol_df["volume"], height=250)

    def _intensity_section(self):
        st.subheader("Intensity")

        per_session = self.session_metrics.get("per_session", {})
        global_m = self.session_metrics.get("global", {})

        if not per_session:
            return

        total_sets = sum(s["total_sets"] for s in per_session.values())
        failure_sets = sum(s["sets_to_failure"] for s in per_session.values())

        failure_pct = ((failure_sets / total_sets) * 100 if total_sets else 0)

        c1, c2 = st.columns(2)

        c1.metric("Avg Intensity", round(global_m.get("avg_intensity", 0), 2) if global_m.get("avg_intensity")else "—")
        c2.metric("Sets to Failure %", round(failure_pct, 1))

        # --- Insight ---
        if failure_pct < 5:
            st.info("You rarely reach failure. " "Consider pushing harder on key lifts.")
        elif failure_pct < 25:
            st.success("Good intensity balance. " "You train hard without overdoing it.")
        else:
            st.warning("High failure rate may hurt recovery." "Monitor fatigue.")

    def _balance_section(self):
        st.subheader("Balance")

        per_ex = self.exercise_metrics.get("per_exercise", {})

        if not per_ex:
            return

        df = pd.DataFrame(per_ex).T

        if "body_part" not in df.columns:
            st.info("No body part data available.")
            return

        body_df = (df.groupby("body_part").agg(volume=("total_volume", "sum"), sets=("total_sets", "sum")).sort_values("volume", ascending=False))

        if body_df.empty:
            return

        st.bar_chart(body_df["volume"], height=300)

        most = body_df.index[0]
        least = body_df.index[-1]

        c1, c2 = st.columns(2)
        c1.metric("Most Trained", most)
        c2.metric("Least Trained", least)
