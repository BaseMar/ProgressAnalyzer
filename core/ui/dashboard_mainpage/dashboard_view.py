import streamlit as st
import pandas as pd


class DashboardView:
    def __init__(self, metrics: dict, sets_df: pd.DataFrame, theme):
        """
        Dashboard main view.

        Parameters
        ----------
        metrics : dict
            Output of metrics_engine.compute_all_metrics()
        sets_df : pd.DataFrame
            Raw sets dataframe (used only for tables / charts, never logic)
        theme : ThemeManager
        """
        self.metrics = metrics
        self.sets_df = sets_df
        self.theme = theme

    def render(self):
        self._render_header()
        self._render_kpis()
        self._render_charts()
        self._render_history()

    def _render_header(self):
        st.title("Gym Progress Dashboard")
        
    def _render_kpis(self):
        session = self.metrics["sessions"]["global"]
        frequency = self.metrics["frequency"]["global"]

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Avg Session Duration", f"{round(session['avg_session_duration'], 1)} min" if session["avg_session_duration"] else "—")

        col2.metric("Avg Volume / Session", f"{round(session['avg_volume_per_session'], 0)} kg" if session["avg_volume_per_session"] else "—")

        col3.metric("Avg Sets / Session", round(session["avg_sets_per_session"], 1) if session["avg_sets_per_session"] else "—")

        col4.metric("Sessions / Week", round(frequency["sessions_per_week"], 2) if frequency["sessions_per_week"] else "—")

    def _session_df(self) -> pd.DataFrame:
        rows = [
            {
                "session_id": sid,
                "volume": v["total_volume"],
                "duration": v["duration_minutes"],
            }
            for sid, v in self.metrics["sessions"]["per_session"].items()]
        
        return pd.DataFrame(rows)

    def _render_charts(self):
        df = self._session_df()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Training Volume Over Time")
            st.line_chart(df.set_index("session_id")["volume"])

        with col2:
            st.subheader("Session Duration Over Time")
            st.line_chart(df.set_index("session_id")["duration"])

    def _render_history(self):
        st.subheader("Workout History")
        st.dataframe(self.sets_df.sort_values("SessionDate", ascending=False), use_container_width=True)
