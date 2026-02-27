import pandas as pd
import streamlit as st

class DashboardView:
    def __init__(self, metrics, sets_df: pd.DataFrame):
        self.metrics = metrics
        self.sets_df = sets_df

    def render(self):
        st.title("Workout Dashboard")

        # --------- 1️⃣ KPI ----------
        kpi_cols = st.columns(5)

        sessions_metrics = self.metrics.get("sessions", {})
        per_session = sessions_metrics.get("per_session", {})
        global_metrics = sessions_metrics.get("global", {})

        avg_intensity = global_metrics.get("avg_intensity")
        avg_volume = global_metrics.get("avg_volume_per_session")
        avg_sets = global_metrics.get("avg_sets_per_session")
        avg_sessions_per_week = global_metrics.get("avg_sessions_per_week")
        avg_duration = global_metrics.get("avg_session_duration")

        kpi_cols[0].metric("Avg Intensity", f"{round(avg_intensity, 2)} %" if avg_intensity is not None else "—")
        kpi_cols[1].metric("Sessions / Week", round(avg_sessions_per_week, 2) if avg_sessions_per_week else "—")
        kpi_cols[2].metric("Avg Volume / Session", round(avg_volume, 1) if avg_volume else "—")
        kpi_cols[3].metric("Avg Sets / Session", round(avg_sets, 1) if avg_sets else "—")
        kpi_cols[4].metric("Avg Session Duration (min)", round(avg_duration, 1) if avg_duration else "—")

        # --------- 2️⃣ Trends ----------
        st.subheader("Session Trends")

        trend_rows = []
        for s in per_session.values():
            if s.get("session_date") is None:
                continue
            trend_rows.append({
                "Date": s["session_date"],
                "Volume": s.get("total_volume"),
                "Duration (min)": s.get("duration_minutes"),
            })

        if trend_rows:
            trend_df = pd.DataFrame(trend_rows).sort_values("Date")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Volume per Session**")
                st.line_chart(trend_df.set_index("Date")[["Volume"]],height=300)

            with col2:
                st.markdown("**Session Duration (min)**")
                st.line_chart(trend_df.set_index("Date")[["Duration (min)"]],height=300,)
        else:
            st.info("No data available to display trends.")

        # --------- 3️⃣ Session History ----------
        st.subheader("Session History")

        df = self.sets_df.copy()
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])
        df = df.sort_values("SessionDate", ascending=False)

        for session_date, session_df in df.groupby("SessionDate"):
            total_volume = (session_df["Repetitions"] * session_df["Weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["ExerciseName"].nunique()

            with st.expander(f"{session_date.date()} — {total_sets} sets, {exercises_count} exercises, Volume: {int(total_volume)}",
                             icon=":material/archive:" ):
                for exercise, ex_df in session_df.groupby("ExerciseName"):
                    st.markdown(f"**{exercise}**")
                    sets_str = " | ".join(
                        f"{row['SetNumber']}×{row['Repetitions']} @ {row['Weight']}kg"
                        for _, row in ex_df.iterrows()
                    )
                    st.markdown(f"`{sets_str}`")
