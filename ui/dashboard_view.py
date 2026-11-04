"""
Dashboard View

Main training dashboard with session-level KPIs, trends, and history.

Responsibilities:
  - Render global training metrics (avg intensity, sessions/week, volume)
  - Display volume and duration trends over time
  - Show session history with exercise breakdowns

All metrics are pre-computed; this view only handles presentation.
"""

from __future__ import annotations

from calendar import Calendar, monthrange
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st
from data_manager import DataManager
from ui.plan_schedule_view import PlanScheduleView

from ui.utils.ui_helpers import chart_label, format_number, line_chart, page_title, section_header


def _set_pills(ex_df: pd.DataFrame) -> str:
    """Render set card badges for display in session history.
    
    Args:
        ex_df: DataFrame of sets for an exercise
    
    Returns:
        HTML string with set pill badges (reps × weight)
    """
    pills = []
    for _, row in ex_df.sort_values("set_number").iterrows():
        duration_seconds = row.get("duration_seconds")
        if pd.notna(duration_seconds) and int(duration_seconds) > 0:
            value = _format_seconds(duration_seconds)
        else:
            value = f'{row["repetitions"]} × {row["weight"]:g} kg'
        pills.append(f'<span class="set-pill">{value}</span>')
    return "".join(pills)


class DashboardView:
    """UI view for the main training dashboard.
    
    Displays:
    - Global training KPIs (intensity, frequency, volume, sets)
    - Session trend charts (volume over time, duration over time)
    - Expandable detailed session history with per-exercise breakdowns
    
    Data:
    - metrics: Pre-computed session-level and global metrics
    - sets_df: Raw set data for detailed session rendering
    """

    def __init__(self, metrics: dict, sets_df: pd.DataFrame, selected_month: str | None = None, *, exercise_names=None, data_manager=None) -> None:
        """Initialize with pre-computed metrics and raw set data.
        
        Args:
            metrics: Dictionary with keys 'sessions', 'exercises', 'progress', 'fatigue', 'body'
            sets_df: DataFrame with columns: session_date, ExerciseName, Weight, Repetitions, set_number
        """
        self.metrics = metrics
        self.sets_df = sets_df
        self.selected_month = selected_month
        self.dm = data_manager if data_manager is not None else DataManager()
        self.schedule = PlanScheduleView(self.dm, exercise_names)
        self.scheduled_workouts = []


    def render(self) -> None:
        """Render the complete dashboard view."""
        self._render_title()
        self._render_kpis()
        self._render_trends()
        self._render_history()

    def _render_title(self) -> None:
        """Render page header."""
        page_title("Overview", "Workout Dashboard")

    def _render_kpis(self) -> None:
        """Render global training KPIs."""
        g = self.metrics.get("sessions", {}).get("global", {})

        section_header("Performance Snapshot")

        cols = st.columns(5)
        cols[0].metric("Avg Intensity", f"{format_number(g.get('avg_intensity'), 1)} %" if g.get("avg_intensity") is not None else "—")
        cols[1].metric("Sessions / Week", format_number(g.get("avg_sessions_per_week"), 1) if g.get("avg_sessions_per_week") else "—")
        cols[2].metric("Avg Volume / Session", f"{format_number(g.get('avg_volume_per_session'), 0)} kg" if g.get("avg_volume_per_session") else "—")
        cols[3].metric("Avg Sets / Session",format_number(g.get("avg_sets_per_session"), 1) if g.get("avg_sets_per_session") else "—")
        cols[4].metric("Avg Duration",f"{format_number(g.get('avg_session_duration'), 0)} min" if g.get("avg_session_duration") else "—")

    def _render_trends(self) -> None:
        """Render session trend charts (volume and duration over time)."""
        per_session = self.metrics.get("sessions", {}).get("per_session", {})
        rows = [
            {
                "Date": s["session_date"],
                "Volume (kg)": s.get("total_volume"),
                "Duration (min)": s.get("duration_minutes"),
            }
            for s in per_session.values()
            if s.get("session_date") is not None
        ]

        section_header("Session Trends")

        if not rows:
            st.info("No trend data available yet.")
            return

        trend_df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
        col1, col2 = st.columns(2)

        with col1:
            chart_label("Session Volume")
            line_chart(trend_df, "Volume (kg)")

        with col2:
            chart_label("Session Duration")
            line_chart(trend_df, "Duration (min)")

    def _render_history(self) -> None:
        section_header("Session History")

        df = self.sets_df.copy()
        self.schedule.render_picker()
        if df.empty and self.selected_month in (None, "All time") and self.schedule.plan_id is None:
            st.info("No workout history yet.")
            return

        df = df.reindex(columns=list(dict.fromkeys([*df.columns, "session_date", "session_id"])))
        df["session_date"] = pd.to_datetime(df["session_date"])
        session_counts = df.groupby(df["session_date"].dt.date)["session_id"].nunique()
        with st.container(key="workout_calendar"):
            selected_day = self._render_calendar(session_counts)

        self.schedule.render_day(selected_day, self.scheduled_workouts)

        selected_count = session_counts.get(selected_day, 0)
        st.markdown(
            '<div class="calendar-detail-heading">'
            f'<span>Sessions on {selected_day:%d %b %Y}</span>'
            f'<span class="calendar-count">{selected_count} '
            f'{"session" if selected_count == 1 else "sessions"}</span></div>',
            unsafe_allow_html=True,
        )
        df = df.loc[df["session_date"].dt.date == selected_day]
        if df.empty:
            st.info("No sessions recorded for this day.")
            return

        self._render_day_sessions(df)

    def _render_calendar(self, session_counts: pd.Series) -> date:
        """Render the month card and return its selected date."""
        training_dates = set(session_counts.index)
        title_col, month_col = st.columns([2, 1])
        with title_col:
            st.markdown(
                '<div class="calendar-eyebrow">Training activity</div>',
                unsafe_allow_html=True,
            )
        with month_col:
            if self.selected_month not in (None, "All time"):
                month = date.fromisoformat(f"{self.selected_month}-01")
            else:
                bounds = training_dates | set(self.schedule.version_dates)
                if self.schedule.plan_id is not None:
                    bounds |= {date.today(), date.today() + timedelta(days=365)}
                months = pd.period_range(min(bounds), max(bounds), freq="M")
                default = str(pd.Period(date.today(), freq="M")) if self.schedule.plan_id is not None else str(months[-1])
                month_label = st.selectbox(
                    "History month", [str(value) for value in months],
                    index=[str(value) for value in months].index(default), key="history_month",
                    format_func=lambda value: date.fromisoformat(f"{value}-01").strftime("%B %Y"),
                    label_visibility="collapsed",
                )
                month = date.fromisoformat(f"{month_label}-01")

        self.scheduled_workouts = self.schedule.load_month(month, month.replace(day=monthrange(month.year, month.month)[1]))
        planned_counts = {}
        linked_counts = {}
        for slot in self.scheduled_workouts:
            planned_counts[slot.scheduled_date] = planned_counts.get(slot.scheduled_date, 0) + 1
            if slot.session_id is not None:
                linked_counts[slot.scheduled_date] = linked_counts.get(slot.scheduled_date, 0) + 1

        month_dates = sorted(day for day in training_dates if (day.year, day.month) == (month.year, month.month))
        month_sessions = sum(session_counts[day] for day in month_dates)
        st.markdown(
            '<div class="calendar-heading">'
            f'<div class="calendar-month">{month:%B} <span>{month:%Y}</span></div>'
            '<div class="calendar-summary">'
            f'<span><strong>{len(month_dates)}</strong> training days</span>'
            f'<span><strong>{month_sessions}</strong> sessions</span>'
            + (f'<span><strong>{len(self.scheduled_workouts)}</strong> planned</span>' if self.schedule.plan_id is not None else '') +
            '</div></div>',
            unsafe_allow_html=True,
        )
        selection_key = f"history_day_{month:%Y-%m}"
        if selection_key not in st.session_state:
            st.session_state[selection_key] = month_dates[-1] if month_dates else month

        with st.container(key="calendar_grid"):
            for col, weekday in zip(st.columns(7, gap="small"), ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
                col.markdown(f'<div class="calendar-weekday">{weekday}</div>', unsafe_allow_html=True)
            for week in Calendar(firstweekday=0).monthdayscalendar(month.year, month.month):
                for col, day_number in zip(st.columns(7, gap="small"), week):
                    if not day_number:
                        col.markdown('<div class="calendar-blank" aria-hidden="true"></div>', unsafe_allow_html=True)
                        continue
                    day = month.replace(day=day_number)
                    count = session_counts.get(day, 0)
                    planned = planned_counts.get(day, 0)
                    state = "trained" if count else "rest"
                    if planned:
                        state = "trained_planned" if count else "planned"
                        if linked_counts.get(day, 0) == planned:
                            state += "_linked"
                    today = "_today" if day == date.today() else ""
                    with col.container(key=f"calendar_cell_{state}_{day.isoformat()}{today}"):
                        st.button(
                            str(day_number), key=f"history_date_{day.isoformat()}",
                            type="primary" if day == st.session_state[selection_key] else "secondary",
                            use_container_width=True,
                            help=f"{day:%d %b %Y}: {count} session(s)"
                            + (f" · {planned} planned · {linked_counts.get(day, 0)} linked" if planned else "")
                            + (" · Today" if today else ""),
                            on_click=st.session_state.__setitem__, args=(selection_key, day),
                        )
        st.markdown(
            '<div class="calendar-footer">'
            '<div class="calendar-legend">'
            '<span><i class="calendar-legend-dot"></i> Workout</span>'
            '<span><i class="calendar-legend-selected"></i> Selected</span>'
            + ('<span><i class="calendar-legend-planned"></i> Planned</span>'
               '<span><i class="calendar-legend-linked"></i> Linked</span>' if self.schedule.plan_id is not None else '') +
            '</div><span>Select a day to explore your sessions</span></div>',
            unsafe_allow_html=True,
        )
        return st.session_state[selection_key]

    def _render_day_sessions(self, df: pd.DataFrame) -> None:
        """Render the existing session cards for the chosen day."""
        grouped = df.groupby(["session_id", "session_date"], sort=False)

        for (session_id, session_date), session_df in grouped:
            total_volume = (session_df["repetitions"] * session_df["weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["exercise_name"].nunique()
            volume_str = f"{total_volume:,.0f}".replace(",", "\u202f")

            label = (
                f"{session_date.strftime('%d %b %Y')}   ·   "
                f"{total_sets} sets   ·   "
                f"{exercises_count} exercises   ·   "
                f"{volume_str} kg"
            )

            with st.expander(label, icon=":material/event:", expanded=True):
                for exercise, ex_df in session_df.groupby("exercise_name"):
                    st.markdown(
                        f'<p class="exercise-label">{escape(str(exercise))}</p>'
                        f'<div class="set-pills">{_set_pills(ex_df)}</div>',
                        unsafe_allow_html=True,
                    )
                
                st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([0.8, 0.2])
                with col2:
                    if st.button("Delete Session", key=f"del_{session_id}", type="secondary", use_container_width=True, icon=":material/delete:"):
                        if self.dm.delete_session(session_id):
                            st.cache_data.clear()
                            st.toast(f"Session deleted successfully!")
                            st.rerun()


def _format_seconds(value: int | float) -> str:
    seconds = int(value)
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}:{remaining_seconds:02d}"
    return f"{seconds}s"
