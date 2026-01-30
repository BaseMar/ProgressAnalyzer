from collections import defaultdict
from typing import Dict
import pandas as pd
import streamlit as st
import plotly.express as px


class AnalyticsView:
    def __init__(self, metrics: Dict):
        self.session_metrics = metrics.get("sessions", {})
        self.exercise_metrics = metrics.get("exercises", {})
        self.progress_metrics = metrics.get("progress", {})

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
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Sessions / Week", round(global_m.get("avg_sessions_per_week", 0), 2))
        
        dur = global_m.get("avg_session_duration")
        c2.metric("Avg Duration (min)", round(dur, 1) if dur else "—")

        sets = global_m.get("avg_sets_per_session")
        c3.metric("Avg Sets / Session", round(sets, 1) if sets else "—",)

        streak = self.streak_counter(per_session)
        c4.metric("Current Streak (weeks)", streak)

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
            st.bar_chart(df.set_index("year_week")["sessions"], height=250)

    def _progress_section(self):
        st.subheader("Progress")

        per_ex = self.progress_metrics.get("per_exercise", {})
        if not per_ex:
            st.info("No progress data.")
            return

        df = pd.DataFrame(per_ex).T

        if "progress_pct" not in df.columns:
            st.info("Missing progress data.")
            return

        if "exposure_count" not in df.columns:
            df["exposure_count"] = 1

        median_progress = df["progress_pct"].median()
        improving = (df["progress_pct"] > 2).sum()
        progress_ratio = improving / len(df) * 100
        plateau_count = (df["progress_pct"].abs() < 2).sum()
        best = df.loc[df["progress_pct"].idxmax()]
        worst = df.loc[df["progress_pct"].idxmin()]

        df["progress_per_exposure"] = (df["progress_pct"] / df["exposure_count"])
        ppe = df["progress_per_exposure"].median()

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Median Progress %", round(median_progress,1))
        c2.metric("Progress Ratio", f"{round(progress_ratio)}%")
        c3.metric("Plateaus", int(plateau_count))
        c4.metric("Top Improver", f"{round(best['progress_pct'],1)}%")
        c5.metric("Top Regressor", f"{round(worst['progress_pct'],1)}%")

        st.metric("Progress / Exposure", round(ppe,2), help="Median % gain per workout exposure")

        st.markdown("### Strength Progress by Exercise")
        chart_df = df.sort_values("progress_pct",ascending=False).head(10).set_index("exercise_name")
        st.bar_chart(chart_df["progress_pct"], height=300)

        st.markdown("### Coach Insight")
        if progress_ratio > 70:
            st.success("Program is highly effective. Most lifts progressing.")
        elif plateau_count > len(df)*0.4:
            st.warning("Many lifts are plateauing. Consider progression changes or deload.")
        elif (df["progress_pct"] < 0).sum() > improving:
            st.error("More lifts regressing than improving. Recovery or load management may be limiting progress.")
        else:
            st.info("Progress is steady. Stay consistent.")

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

    def streak_counter(self, per_session: Dict) -> int:
        """Calculate the current workout streak in weeks if i go 3+ days.

        Parameters
        ----------
        per_session : Dict
            Dictionary of session-level metrics.

        Returns
        -------
        int
            Current streak in weeks.
        """
        
        # calculate number of sessions per week
        sessions_per_week = defaultdict(int)
        for date in per_session.values():
            if date.get("session_date"):
                d = pd.to_datetime(date["session_date"])
                iso = d.isocalendar()
                year_week = (iso.year, iso.week)
                sessions_per_week[year_week] += 1

        # calculate weeks with 3+ sessions
        good_weeks = sorted((yw for yw, cnt in sessions_per_week.items() if cnt >= 3))

        # calculate current streak
        current_streak = 1
        for i in range(len(good_weeks) - 1, 0, -1):
            year, week = good_weeks[i]
            prev_year, prev_week = good_weeks[i - 1]

            # check if previous week is consecutive
            if (year == prev_year and week == prev_week + 1) or (year == prev_year + 1 and week == 1 and prev_week == 52):
                current_streak += 1
            else:
                break
        return current_streak