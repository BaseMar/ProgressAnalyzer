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

        total_sessions = len(per_session)
        avg_volume = global_metrics.get("avg_volume_per_session")
        avg_sets = global_metrics.get("avg_sets_per_session")
        avg_sessions_per_week = global_metrics.get("avg_sessions_per_week")
        avg_duration = global_metrics.get("avg_session_duration")

        kpi_cols[0].metric("Liczba sesji", total_sessions)
        kpi_cols[1].metric("Sesje / tydzień",round(avg_sessions_per_week, 2) if avg_sessions_per_week else "—",)
        kpi_cols[2].metric("Średni wolumen / sesja",round(avg_volume, 1) if avg_volume else "—",)
        kpi_cols[3].metric("Średnia liczba serii / sesja",round(avg_sets, 1) if avg_sets else "—",)
        kpi_cols[4].metric("Średni czas sesji (min)",round(avg_duration, 1) if avg_duration else "—",)

        # --------- 2️⃣ Trendy ----------
        st.subheader("Trendy sesji")

        # przygotowanie danych
        trend_rows = []
        for s in per_session.values():
            if s.get("session_date") is None:
                continue
            trend_rows.append({
                "Data": s["session_date"],
                "Wolumen": s.get("total_volume"),
                "Czas (min)": s.get("duration_minutes"),
            })

        if trend_rows:
            trend_df = pd.DataFrame(trend_rows).sort_values("Data")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Wolumen na sesję**")
                st.line_chart(
                    trend_df.set_index("Data")[["Wolumen"]],
                    height=300,
                )

            with col2:
                st.markdown("**Czas trwania sesji (min)**")
                st.line_chart(
                    trend_df.set_index("Data")[["Czas (min)"]],
                    height=300,
                )
        else:
            st.info("Brak danych do wyświetlenia trendów.")

        # --------- 3️⃣ Historia sesji ----------
        st.subheader("Historia sesji")

        df = self.sets_df.copy()
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])
        df = df.sort_values("SessionDate", ascending=False)

        for session_date, session_df in df.groupby("SessionDate"):
            total_volume = (session_df["Repetitions"] * session_df["Weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["ExerciseName"].nunique()

            with st.expander(f"📅 {session_date.date()} — {total_sets} serie, {exercises_count} ćwiczenia, Wolumen: {int(total_volume)}"):
                for exercise, ex_df in session_df.groupby("ExerciseName"):
                    st.markdown(f"**{exercise}**")
                    sets_str = " | ".join(
                        f"{row['SetNumber']}×{row['Repetitions']} @ {row['Weight']}kg"
                        for _, row in ex_df.iterrows()
                    )
                    st.markdown(f"`{sets_str}`")
