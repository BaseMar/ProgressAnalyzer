import streamlit as st
from typing import Any, Optional, cast

import pandas as pd

from ...services.history_service import HistoryService
from ...styles.theme_manager import ThemeManager


class HistoryView:
    """Enhanced history view with better navigation"""

    def __init__(self, df_sets: Any, theme: ThemeManager) -> None:
        self.service: HistoryService = HistoryService(df_sets)
        self.theme: ThemeManager = theme

    def render(self) -> None:
        """Render full history view"""
        st.header("Workout History")

        weeks_raw: Any = self.service.get_weeks()
        # Normalize to a list of (year:int, week:int) tuples so types are explicit
        weeks = [(int(r[0]), int(r[1])) for r in weeks_raw] if weeks_raw is not None else []
        if not weeks:
            st.info("No workout data available.")
            return

        self._render_week_navigation(weeks)
        self._render_week_details(weeks)

    def _render_week_navigation(self, weeks: Any) -> None:
        """Render week navigation controls"""
        current_idx: int = st.session_state.get("current_week_idx", len(weeks) - 1)

        col_prev, col_info, col_next = st.columns([1, 3, 1])

        with col_prev:
            if st.button("⬅️ Previous", key="hist_prev") and current_idx > 0:
                st.session_state.current_week_idx = current_idx - 1
                st.rerun()

        with col_info:
                year_week = weeks[current_idx]
                # year_week may be a numpy record or tuple - cast to ints for safety
                year = int(year_week[0])
                week = int(year_week[1])
                st.markdown(
                    f"<h3 style='text-align: center;'>Week {week} / {year}</h3>",
                    unsafe_allow_html=True,
                )

        with col_next:
            if st.button("➡️ Next", key="hist_next") and current_idx < len(weeks) - 1:
                st.session_state.current_week_idx = current_idx + 1
                st.rerun()

    def _render_week_details(self, weeks: Any) -> None:
        """Render detailed week information"""
        current_idx: int = st.session_state.get("current_week_idx", len(weeks) - 1)
        year_week = weeks[current_idx]
        year = year_week[0]
        week = year_week[1]

        # mypy: underlying service returns Optional[list[dict]] where year/week may be numpy types.
        # Use a narrow, runtime-validated call and ignore this specific arg-type complaint.
        week_sessions: Optional[list[dict[str, object]]] = self.service.get_week_sessions(
            year, week
        )  # type: ignore[arg-type]

        if not week_sessions:
            st.warning("No workouts in this week.")
            return

        for i, session in enumerate(week_sessions):
            # `session['date']` is a pandas Timestamp; cast for type-checking
            session_date = cast(pd.Timestamp, session["date"])
            st.markdown(f"#### Session {i+1} - {session_date.strftime('%Y-%m-%d')}")

            col1, col2 = st.columns(2)
            with col1:
                total_sets = int(cast(int, session["total_sets"]))
                st.metric("Number of Sets", total_sets)
            with col2:
                total_vol = (
                    float(cast(float, session["total_volume"]))
                    if session.get("total_volume") is not None
                    else 0.0
                )
                st.metric("Volume", f"{total_vol:.0f} kg")

            with st.expander("Show Exercise Details"):
                exercises_df = cast(pd.DataFrame, session["exercises"])
                for _, ex in exercises_df.iterrows():
                    ex_vol = (
                        float(cast(float, ex["total_volume"]))
                        if ex.get("total_volume") is not None
                        else 0.0
                    )
                    st.markdown(
                        f"• **{ex['ExerciseName']}** — {ex['sets']} sets, "
                        f"{ex['total_reps']} reps, volume: {ex_vol:.0f} kg"
                    )
