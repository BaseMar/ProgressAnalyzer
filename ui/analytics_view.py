from typing import Dict
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff


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

        # --- Heatmap ---
        st.markdown("### Progress Heatmap per Exercise vs Session")
       
        progress_data = []
        for ex_id, ex in per_ex.items():
            for i, date_entry in enumerate(range(ex.get("exposure_count",0))):
                progress_data.append({
                    "Exercise": ex["exercise_name"],
                    "Session": i+1,
                    "Progress (%)": round(ex["progress_pct"]/ex.get("exposure_count",1),2)
                })
        
        heat_df = pd.DataFrame(progress_data)
        if not heat_df.empty:
            heat_pivot = heat_df.pivot(index="Exercise", columns="Session", values="Progress (%)").fillna(0)
            fig_heat = ff.create_annotated_heatmap(
                z=heat_pivot.values,
                x=[f"Session {i}" for i in heat_pivot.columns],
                y=heat_pivot.index.tolist(),
                colorscale="Viridis",
                showscale=True,
                annotation_text=heat_pivot.round(1).values
            )
            fig_heat.update_layout(height=400, margin=dict(l=100, r=40, t=40, b=40))
            st.plotly_chart(fig_heat, width='stretch')

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