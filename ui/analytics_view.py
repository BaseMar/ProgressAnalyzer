from typing import Dict
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff
from datetime import datetime, timedelta


class AnalyticsView:
    def __init__(self, metrics: Dict):
        self.session_metrics = metrics.get("sessions", {})
        self.exercise_metrics = metrics.get("exercises", {})
        self.progress_metrics = metrics.get("progress", {})
        self.fatigue_metrics = metrics.get("fatigue", {})

    def render(self) -> None:
        st.header("Analytics Dashboard")

        self._fatigue_section()
        st.divider()
        self._progress_section()

    def _progress_section(self):
        st.subheader("Strength Progress")

        per_ex = self.progress_metrics.get("per_exercise", {})
        if not per_ex:
            st.info("No progress data.")
            return

        df = pd.DataFrame(per_ex).T
        df["progress_per_exposure"] = df["progress_pct"] / df["exposure_count"]
        df.fillna(0, inplace=True)

        # --- KPI ---
        median_progress = df["progress_pct"].median()
        improving = (df["progress_pct"] > 2).sum()
        plateau_count = ((df["progress_pct"].abs() < 2).sum())
        progress_ratio = improving / len(df) * 100 if len(df) else 0
        top_exercise = df.loc[df['progress_pct'].idxmax()]['exercise_name']
        worst_exercise = df.loc[df['progress_pct'].idxmin()]['exercise_name']
        

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Median Progress (%)", round(median_progress, 1))
        c2.metric("Progress Ratio (%)", f"{round(progress_ratio)}%")
        c3.metric("Plateaus", int(plateau_count))
        c4.metric("Top Improver (%)", f"{top_exercise}")
        c5.metric("Top Regressor (%)", f"{worst_exercise}")

        # --- Top/Bottom 10 Bar Chart ---
        top10 = df.sort_values("progress_pct", ascending=False).head(10)
        bottom10 = df.sort_values("progress_pct", ascending=True).head(10)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top 10 Exercises**")
            fig_top = px.bar(
                top10,
                x="exercise_name",
                y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "Exercise", "progress_pct": "Strength Progress (%)"},
            )
            fig_top.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            st.plotly_chart(fig_top, width='stretch')

        with col2:
            st.markdown("**Bottom 10 Exercises**")
            fig_bottom = px.bar(
                bottom10,
                x="exercise_name",
                y="progress_pct",
                text="progress_pct",
                labels={"exercise_name": "Exercise", "progress_pct": "Strength Progress (%)"},
            )
            fig_bottom.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            st.plotly_chart(fig_bottom, width='stretch')

        # --- Plateau Detection & Smart Recommendations ---
        st.markdown("### Plateau Zone Analysis & Interventions")

        per_ex = self.progress_metrics.get("per_exercise", {})
        exercise_per = self.exercise_metrics.get("per_exercise", {})

        # Build enriched plateau data with recency info
        plateau_data = []
        abandoned_data = []
        today = datetime.now().date()
        recency_threshold_days = 28  # Only flag as active plateau if trained in last 28 days

        for ex_id, progress_row in per_ex.items():
            if abs(progress_row["progress_pct"]) >= 2:
                continue  # Skip improving/regressing exercises

            ex_name = progress_row["exercise_name"]
            progress = progress_row["progress_pct"]
            exposure = progress_row["exposure_count"]

            # Get last training date from exercise_metrics
            ex_info = exercise_per.get(ex_id, {})
            per_session_1rm = ex_info.get("per_session_1rm", [])
            
            last_date = None
            if per_session_1rm:
                last_date = pd.to_datetime(per_session_1rm[-1]["date"]).date()

            days_since = (today - last_date).days if last_date else None

            if days_since is None:
                continue  # Skip if no date info

            if days_since <= recency_threshold_days:
                # Active plateau - being trained recently
                plateau_data.append({
                    "exercise_id": ex_id,
                    "exercise_name": ex_name,
                    "progress_pct": progress,
                    "exposure_count": exposure,
                    "last_date": last_date,
                    "days_since": days_since,
                })
            else:
                # Abandoned - not trained recently
                abandoned_data.append({
                    "exercise_id": ex_id,
                    "exercise_name": ex_name,
                    "progress_pct": progress,
                    "exposure_count": exposure,
                    "last_date": last_date,
                    "days_since": days_since,
                })

        # Sort by exposure count (priority for action)
        plateau_data = sorted(plateau_data, key=lambda x: x["exposure_count"], reverse=True)
        abandoned_data = sorted(abandoned_data, key=lambda x: x["days_since"], reverse=True)

        # --- Display Active Plateaus ---
        if not plateau_data:
            st.success("✅ No active exercises in plateau zone! All recently trained exercises are either progressing or regressing.")
        else:
            st.info(f"⚠️ **{len(plateau_data)} active exercise(s)** stuck in plateau (trained in last {recency_threshold_days} days)")
            
            for idx, item in enumerate(plateau_data):
                ex_name = item["exercise_name"]
                progress = item["progress_pct"]
                exposure = item["exposure_count"]
                days_since = item["days_since"]
                
                # Build recommendation logic
                recs = []
                if exposure < 5:
                    recs.append("📈 **Increase Frequency** — Less than 5 sessions; 2-3x/week for better adaptation signal")
                elif exposure >= 12:
                    recs.append("💪 **Boost Volume or Intensity** — 12+ exposures; try +10% weight, change rep range, or add drop sets")
                else:
                    recs.append("🔄 **Change Stimulus** — Moderate frequency; try new angle, tempo (3-0-1), pause reps, or variation")
                
                if progress < -0.5:
                    recs.append("⚙️ **Form Check** — Slight regression; review technique or consider deload week")
                else:
                    recs.append("✓ **Stabilizing** — Minor fluctuations; maintain current approach or progress incrementally")

                with st.expander(f"**{ex_name}** — Progress: {progress:.1f}% | Exposures: {int(exposure)} | Last: {days_since}d ago", expanded=(idx == 0)):
                    for rec in recs:
                        st.markdown(rec)

        # --- Display Abandoned Exercises ---
        if abandoned_data:
            st.divider()
            st.markdown("#### Abandoned Exercises")
            st.caption(f"Not trained in {recency_threshold_days}+ days (no active intervention needed)")
            
            for item in abandoned_data:
                ex_name = item["exercise_name"]
                progress = item["progress_pct"]
                days_since = item["days_since"]
                
                st.markdown(f"• **{ex_name}** — Progress: {progress:.1f}% | Last trained: {days_since} days ago")

    def _fatigue_section(self):
        st.subheader("Fatigue & Recovery")

        per_session = self.fatigue_metrics.get("per_session", {})
        global_f = self.fatigue_metrics.get("global", {})

        if not per_session:
            st.info("No fatigue data.")
            return

        # ---------- KPI ----------
        # avg intensity + sets to failure z session metrics
        total_sets = sum(s["total_sets"] for s in self.session_metrics.get("per_session", {}).values())
        failure_sets = sum(s["sets_to_failure"] for s in self.session_metrics.get("per_session", {}).values())
        failure_pct = (failure_sets / total_sets * 100) if total_sets else 0
        avg_intensity = self.session_metrics.get("global", {}).get("avg_intensity",0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Fatigue Score", global_f.get("avg_fatigue_score","—"))
        c2.metric("% High Fatigue Sessions", global_f.get("high_fatigue_sessions_ratio","—"))
        c3.metric("Max Consecutive High Fatigue", global_f.get("max_consecutive_high_fatigue_sessions","—"))
        c4.metric("Avg Session Intensity", f"{round(avg_intensity,2)}%")

        st.markdown(f"**Sets to Failure (%)**: {round(failure_pct,1)}%")

        # ---------- Fatigue Trend ----------
        df = pd.DataFrame([
            {
                "session_id": sid,
                "date": s.get("session_date"),
                "fatigue_score": s.get("fatigue_score",0)
            } for sid,s in per_session.items()
        ])
        df = df.dropna(subset=["date"])
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            fig_line = px.line(df, x="date", y="fatigue_score", markers=True,
                               labels={"date":"Session Date", "fatigue_score":"Fatigue Score"},
                               title="Fatigue Score Over Time")
            st.plotly_chart(fig_line, width='stretch')

        # ---------- Insight ----------
        if global_f.get("high_fatigue_sessions_ratio",0) > 0.3:
            st.warning("High frequency of fatigue-heavy sessions – monitor recovery!")
        else:
            st.success("Fatigue levels are balanced. Keep consistency.")