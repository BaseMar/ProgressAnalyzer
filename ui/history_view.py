"""One home for workout logs, import, plan assignments and source corrections."""

from __future__ import annotations

import logging
from calendar import Calendar, monthrange
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from mapper import map_workout_set
from ui.body_metrics_view import BodyMetricsView
from ui.exercise_replacements_view import ExerciseReplacementsView
from ui.plan_schedule_view import PlanScheduleView
from ui.set_load_view import render_set_load_correction
from ui.sidebar_upload import SidebarUpload
from ui.utils.active_plan import select_active_plan
from ui.utils.set_load_inputs import format_load
from ui.utils.ui_helpers import page_title, section_header
from ui.workout_entry_view import render_workout_entry

logger = logging.getLogger(__name__)


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
            if pd.isna(row.get("load_type")) and pd.notna(row.get("weight")) and row["weight"] > 0:
                value += f" · logged load {row['weight']:g} kg"
        else:
            value = f"{row['repetitions']} × {row['weight']:g} kg"
        if not pd.isna(row.get("load_type")):
            load_text = format_load(map_workout_set(row.to_dict()).load)
            value = (
                f"{_format_seconds(duration_seconds)} · "
                if pd.notna(duration_seconds) and duration_seconds > 0
                else f"{row['repetitions']} × "
            ) + load_text
        if pd.notna(row.get("is_warmup")) and bool(row.get("is_warmup")):
            value = f"WU · {value}"
        pills.append(f'<span class="set-pill">{value}</span>')
    return "".join(pills)


class HistoryView:
    """Recorded workouts with optional input and correction controls."""

    def __init__(
        self,
        metrics: dict,
        sets_df: pd.DataFrame,
        selected_month: str | None = None,
        *,
        exercise_names=None,
        data_manager=None,
    ) -> None:
        """Initialize with pre-computed metrics and raw set data.

        Args:
            metrics: Body measurement timeline used by the entry form.
            sets_df: Recorded sets with dates, exercise names, loads and quantities.
        """
        self.metrics = metrics
        self.sets_df = sets_df
        self.selected_month = selected_month
        self.dm = data_manager if data_manager is not None else DataManager()
        self.exercise_names = exercise_names or {}
        self.schedule = PlanScheduleView(self.dm)
        self.scheduled_workouts = []

    def render(self) -> None:
        page_title("History", "Your training history")
        if "history_workout_notice" in st.session_state:
            st.success(st.session_state.pop("history_workout_notice"))
        workout_action, measurement_action = st.columns(2)
        if workout_action.button(
            "Add workout", key="history_add_workout_button", icon=":material/add:"
        ):
            st.session_state["history_add_workout"] = True
        if measurement_action.button(
            "Add body measurement",
            key="history_add_measurement_button",
            icon=":material/straighten:",
        ):
            st.session_state["history_add_measurement"] = not st.session_state.get(
                "history_add_measurement", False
            )
        if st.session_state.get("history_add_workout"):
            with st.container(key="history_import"):
                if st.button("Close entry", key="history_close_import"):
                    st.session_state["history_add_workout"] = False
                    st.rerun()
                mode = st.radio(
                    "Workout entry",
                    ["Import TXT", "Enter exercise"],
                    horizontal=True,
                    key="workout_entry_mode",
                )
                if mode == "Import TXT":
                    SidebarUpload(manager=self.dm).render()
                else:
                    render_workout_entry(self.dm)
        if st.session_state.get("history_add_measurement"):
            BodyMetricsView(self.metrics.get("body", {}), manager=self.dm)._add_measurement_form()
        self._select_plan()
        if self.schedule.plan_id is not None and not st.toggle(
            "Show planned workouts", value=True, key="calendar_plan_overlay"
        ):
            self.schedule.plan_id = None
            self.schedule.version_dates = []
        self._render_history()

    def _select_plan(self):
        try:
            if not self.dm.plan_schedule_storage_ready():
                return
            plans = self.dm.load_training_plans()
            self.schedule.plan_id = select_active_plan(plans)
            if self.schedule.plan_id is not None:
                self.schedule.version_dates = [
                    version.draft.effective_from
                    for version in self.dm.load_training_plan_versions(self.schedule.plan_id)
                ]
        except SQLAlchemyError:
            logger.exception("Unable to load history plan")
            st.warning("Plan overlay is unavailable. Recorded sessions remain accessible.")

    def _render_history(self) -> None:
        section_header("Session History")

        df = self.sets_df.copy()
        if df.empty and self.selected_month in (None, "All time") and self.schedule.plan_id is None:
            st.info("No workout history yet.")
            return

        df = df.reindex(columns=list(dict.fromkeys([*df.columns, "session_date", "session_id"])))
        df["session_date"] = pd.to_datetime(df["session_date"])
        session_counts = df.groupby(df["session_date"].dt.date)["session_id"].nunique()
        with st.container(key="workout_calendar"):
            selected_day = self._render_calendar(session_counts)

        self.schedule.render_day(selected_day, self.scheduled_workouts)
        linked = [
            slot
            for slot in self.scheduled_workouts
            if slot.scheduled_date == selected_day and slot.session_id is not None
        ]
        if linked and self.schedule.plan_id is not None:
            with st.expander("Confirm exercise replacements"):
                try:
                    data = self.dm.load_plan_adherence(
                        self.schedule.plan_id, selected_day, selected_day
                    )
                    ExerciseReplacementsView(self.dm, self.exercise_names).render(data)
                except SQLAlchemyError:
                    st.error("Replacement data could not be loaded. Please try again.")

        selected_count = session_counts.get(selected_day, 0)
        st.markdown(
            '<div class="calendar-detail-heading">'
            f"<span>Sessions on {selected_day:%d %b %Y}</span>"
            f'<span class="calendar-count">{selected_count} '
            f"{'session' if selected_count == 1 else 'sessions'}</span></div>",
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
                default = (
                    str(pd.Period(date.today(), freq="M"))
                    if self.schedule.plan_id is not None
                    else str(months[-1])
                )
                choices = [str(value) for value in months]
                saved = st.session_state.get("history_calendar_month")
                if st.session_state.get("history_month") not in choices:
                    st.session_state["history_month"] = saved if saved in choices else default
                month_label = st.selectbox(
                    "History month",
                    choices,
                    key="history_month",
                    format_func=lambda value: date.fromisoformat(f"{value}-01").strftime("%B %Y"),
                    label_visibility="collapsed",
                )
                st.session_state["history_calendar_month"] = month_label
                month = date.fromisoformat(f"{month_label}-01")

        self.scheduled_workouts = self.schedule.load_month(
            month, month.replace(day=monthrange(month.year, month.month)[1])
        )
        planned_counts = {}
        linked_counts = {}
        for slot in self.scheduled_workouts:
            planned_counts[slot.scheduled_date] = planned_counts.get(slot.scheduled_date, 0) + 1
            if slot.session_id is not None:
                linked_counts[slot.scheduled_date] = linked_counts.get(slot.scheduled_date, 0) + 1

        month_dates = sorted(
            day for day in training_dates if (day.year, day.month) == (month.year, month.month)
        )
        month_sessions = sum(session_counts[day] for day in month_dates)
        st.markdown(
            '<div class="calendar-heading">'
            f'<div class="calendar-month">{month:%B} <span>{month:%Y}</span></div>'
            '<div class="calendar-summary">'
            f"<span><strong>{len(month_dates)}</strong> training days</span>"
            f"<span><strong>{month_sessions}</strong> sessions</span>"
            + (
                f"<span><strong>{len(self.scheduled_workouts)}</strong> planned</span>"
                if self.schedule.plan_id is not None
                else ""
            )
            + "</div></div>",
            unsafe_allow_html=True,
        )
        selection_key = f"history_day_{month:%Y-%m}"
        if selection_key not in st.session_state:
            st.session_state[selection_key] = month_dates[-1] if month_dates else month

        with st.container(key="calendar_grid"):
            for col, weekday in zip(
                st.columns(7, gap="small"), ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            ):
                col.markdown(
                    f'<div class="calendar-weekday">{weekday}</div>', unsafe_allow_html=True
                )
            for week in Calendar(firstweekday=0).monthdayscalendar(month.year, month.month):
                for col, day_number in zip(st.columns(7, gap="small"), week):
                    if not day_number:
                        col.markdown(
                            '<div class="calendar-blank" aria-hidden="true"></div>',
                            unsafe_allow_html=True,
                        )
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
                            str(day_number),
                            key=f"history_date_{day.isoformat()}",
                            type="primary"
                            if day == st.session_state[selection_key]
                            else "secondary",
                            use_container_width=True,
                            help=f"{day:%d %b %Y}: {count} session(s)"
                            + (
                                f" · {planned} planned · {linked_counts.get(day, 0)} linked"
                                if planned
                                else ""
                            )
                            + (" · Today" if today else ""),
                            on_click=st.session_state.__setitem__,
                            args=(selection_key, day),
                        )
        st.markdown(
            '<div class="calendar-footer">'
            '<div class="calendar-legend">'
            '<span><i class="calendar-legend-dot"></i> Workout</span>'
            '<span><i class="calendar-legend-selected"></i> Selected</span>'
            + (
                '<span><i class="calendar-legend-planned"></i> Planned</span>'
                '<span><i class="calendar-legend-linked"></i> Linked</span>'
                if self.schedule.plan_id is not None
                else ""
            )
            + "</div><span>Select a day to explore your sessions</span></div>",
            unsafe_allow_html=True,
        )
        return st.session_state[selection_key]

    def _render_day_sessions(self, df: pd.DataFrame) -> None:
        """Render the existing session cards for the chosen day."""
        from ui.set_classification_view import render_set_classification

        if "is_warmup" in df and df["is_warmup"].eq(True).any():
            st.caption(
                "Log totals preserve all recorded sets. Analysis interprets effort and warm-ups automatically."
            )
        grouped = df.groupby(["session_id", "session_date"], sort=False)

        for (session_id, session_date), session_df in grouped:
            duration = session_df.get(
                "duration_seconds", pd.Series(0, index=session_df.index)
            ).fillna(0)
            dynamic = session_df.loc[duration <= 0]
            total_volume = (dynamic["repetitions"] * dynamic["weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["exercise_name"].nunique()
            volume_str = f"{total_volume:,.0f}".replace(",", "\u202f")

            label = f"{session_date:%d %b %Y}   \u00b7   {total_sets} sets   \u00b7   {exercises_count} exercises"
            if (
                not session_df.get("load_type", pd.Series(dtype=str))
                .isin(["bodyweight", "assisted_bodyweight"])
                .any()
                and not dynamic.empty
            ):
                label += f"   \u00b7   {volume_str} kg"

            with st.expander(label, icon=":material/event:", expanded=True):
                for exercise, ex_df in session_df.groupby("exercise_name"):
                    st.markdown(
                        f'<p class="exercise-label">{escape(str(exercise))}</p>'
                        f'<div class="set-pills">{_set_pills(ex_df)}</div>',
                        unsafe_allow_html=True,
                    )
                render_set_classification(self.dm, session_id=int(session_id))
                render_set_load_correction(
                    self.dm, session_id=int(session_id), workout_date=session_date.date()
                )

                st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

                col1, col2 = st.columns([0.8, 0.2])
                with col2:
                    if st.button(
                        "Delete Session",
                        key=f"del_{session_id}",
                        type="secondary",
                        use_container_width=True,
                        icon=":material/delete:",
                    ):
                        if self.dm.delete_session(session_id):
                            st.toast("Session deleted successfully!")
                            st.rerun()


def _format_seconds(value: int | float) -> str:
    seconds = int(value)
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}:{remaining_seconds:02d}"
    return f"{seconds}s"
