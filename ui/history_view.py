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
from ui.load_profiles_view import DATA_SETTINGS_KEY, data_settings_dialog
from ui.plan_schedule_view import PlanScheduleView
from ui.session_plan_link_view import SESSION_LINK_KEY, session_plan_link_dialog
from ui.session_tools_view import SESSION_TOOLS_KEY, session_tools_dialog
from ui.sidebar_upload import SidebarUpload
from ui.utils.active_plan import select_active_plan
from ui.utils.set_load_inputs import format_load
from ui.utils.ui_helpers import page_title, section_header
from ui.workout_entry_view import render_workout_entry

logger = logging.getLogger(__name__)


def _shared_load_description(ex_df: pd.DataFrame) -> str | None:
    """Show a shared body-weight convention once, beside the exercise name."""
    descriptions = []
    for row in ex_df.to_dict("records"):
        if row.get("load_type") not in ("bodyweight", "assisted_bodyweight"):
            return None
        descriptions.append(format_load(map_workout_set(row).load))
    return descriptions[0] if descriptions and len(set(descriptions)) == 1 else None


def _set_results(ex_df: pd.DataFrame, *, shared_load: str | None = None) -> str:
    """Render each recorded set as a separate, single-line result tile."""
    results = []
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
            if shared_load == load_text:
                value = (
                    _format_seconds(duration_seconds)
                    if pd.notna(duration_seconds) and duration_seconds > 0
                    else f"{row['repetitions']} reps"
                )
            else:
                value = (
                    f"{_format_seconds(duration_seconds)} · "
                    if pd.notna(duration_seconds) and duration_seconds > 0
                    else f"{row['repetitions']} × "
                ) + load_text
        if pd.notna(row.get("is_warmup")) and bool(row.get("is_warmup")):
            value = f"WU · {value}"
        rir = row.get("rir")
        reserve = f"RIR {rir:g}" if pd.notna(rir) else "RIR —"
        results.append(
            f'<span class="plan-reference-target history-set-result"><span>{escape(value)}</span>'
            f"<small>Set {int(row['set_number'])} · {reserve}</small></span>"
        )
    return "".join(results)


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
        with st.container(key="history_page_header", horizontal=True, vertical_alignment="center"):
            page_title("History", "Your training history")
            if st.button(
                "Data settings",
                key="history_data_settings_button",
                icon=":material/settings:",
                help="Manage exercise load conventions across all sessions.",
            ):
                st.session_state.pop(SESSION_LINK_KEY, None)
                st.session_state.pop(SESSION_TOOLS_KEY, None)
                st.session_state[DATA_SETTINGS_KEY] = True
        if "history_workout_notice" in st.session_state:
            st.success(st.session_state.pop("history_workout_notice"))
        with st.container(key="history_actions"):
            upload, manual, body = st.columns(3)
            if upload.button(
                "Import workout TXT",
                key="history_add_workout_button",
                width="stretch",
                icon=":material/upload_file:",
            ):
                st.session_state["history_add_workout"] = True
                st.session_state["history_add_measurement"] = False
                st.session_state["workout_entry_mode"] = "Import TXT"
            if manual.button(
                "Enter workout manually",
                key="history_manual_workout_button",
                width="stretch",
                icon=":material/edit_note:",
            ):
                st.session_state["history_add_workout"] = True
                st.session_state["history_add_measurement"] = False
                st.session_state["workout_entry_mode"] = "Enter exercise"
            if body.button(
                "Body measurements",
                key="history_add_measurement_button",
                icon=":material/straighten:",
                width="stretch",
            ):
                st.session_state["history_add_measurement"] = not st.session_state.get(
                    "history_add_measurement", False
                )
                st.session_state["history_add_workout"] = False
        if st.session_state.get("history_add_workout"):
            with st.container(key="history_import"):
                with st.container(key="history_entry_actions"):
                    if st.button(
                        "Close entry", key="history_close_import", icon=":material/close:"
                    ):
                        st.session_state["history_add_workout"] = False
                        st.rerun()
                mode = st.session_state.get("workout_entry_mode", "Import TXT")
                if mode == "Import TXT":
                    SidebarUpload(manager=self.dm).render()
                else:
                    render_workout_entry(self.dm)
        if st.session_state.get("history_add_measurement"):
            with st.container(key="history_measurement_entry"):
                with st.container(key="history_entry_actions"):
                    if st.button(
                        "Close measurements",
                        key="history_close_measurement",
                        icon=":material/close:",
                    ):
                        st.session_state["history_add_measurement"] = False
                        st.rerun()
                BodyMetricsView(
                    self.metrics.get("body", {}), manager=self.dm
                )._add_measurement_form()
        self._render_history()
        if st.session_state.get(DATA_SETTINGS_KEY):
            data_settings_dialog(self.dm)

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
        section_header(
            "Workout history",
            first=not (
                st.session_state.get("history_add_workout")
                or st.session_state.get("history_add_measurement")
            ),
        )

        with st.container(key="history_calendar_panel"):
            with st.container(key="history_calendar_settings"):
                section_header("Calendar settings", first=True)
                plan, overlay = st.columns([3, 1], vertical_alignment="bottom")
                with plan:
                    self._select_plan()
                with overlay:
                    if self.schedule.plan_id is not None and not st.toggle(
                        "Show planned workouts", value=True, key="calendar_plan_overlay"
                    ):
                        self.schedule.plan_id = None
                        self.schedule.version_dates = []
            df = self.sets_df.copy()
            empty = (
                df.empty
                and self.selected_month in (None, "All time")
                and self.schedule.plan_id is None
            )
            if not empty:
                df = df.reindex(
                    columns=list(dict.fromkeys([*df.columns, "session_date", "session_id"]))
                )
                df["session_date"] = pd.to_datetime(df["session_date"])
                session_counts = df.groupby(df["session_date"].dt.date)["session_id"].nunique()
                with st.container(key="workout_calendar"):
                    selected_day = self._render_calendar(session_counts)
        if empty:
            st.info("No workout history yet.")
            return
        with st.container(key="history_workspace"):
            with st.container(key="history_day_details"):
                selected_count = session_counts.get(selected_day, 0)
                st.markdown(
                    '<div class="calendar-detail-heading">'
                    f"<span>Sessions on {selected_day:%d %b %Y}</span>"
                    f'<span class="calendar-count">{selected_count} '
                    f"{'session' if selected_count == 1 else 'sessions'}</span></div>",
                    unsafe_allow_html=True,
                )
                day_df = df.loc[df["session_date"].dt.date == selected_day]
                if day_df.empty:
                    st.info("No sessions recorded for this day.")
                else:
                    self._render_day_sessions(day_df)
                if day_df.empty and self.schedule.plan_id is not None:
                    self._render_day_plan(selected_day)

    def _render_day_plan(self, selected_day):
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

    def _render_calendar(self, session_counts: pd.Series) -> date:
        """Render the month card and return its selected date."""
        training_dates = set(session_counts.index)
        title_col, month_col = st.columns([3, 1], vertical_alignment="center")
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
        title_col.markdown(
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
            + "</div></div>",
            unsafe_allow_html=True,
        )
        return st.session_state[selection_key]

    def _render_day_sessions(self, df: pd.DataFrame) -> None:
        """Display recorded exercises using the same reference list as the plan."""
        assignments = {}
        link_ready = False
        try:
            link_ready = self.dm.plan_schedule_storage_ready()
            if link_ready:
                assignments = self.dm.load_session_plan_assignments(
                    tuple(int(value) for value in df["session_id"].unique())
                )
        except SQLAlchemyError:
            logger.exception("Unable to load session plan links")
            link_ready = False

        grouped = df.groupby(["session_id", "session_date"], sort=False)

        for (session_id, session_date), session_df in grouped:
            total_sets = len(session_df)
            group_key = (
                "workout_exercise_id" if "workout_exercise_id" in session_df else "exercise_name"
            )
            exercises_count = session_df[group_key].nunique()
            current = assignments.get(int(session_id))
            linked_workout = f" · {escape(current['day_name'])}" if current else ""
            with st.container(key=f"history_session_{session_id}"):
                with st.container(
                    key=f"history_session_header_{session_id}",
                    horizontal=True,
                    vertical_alignment="center",
                    gap="small",
                ):
                    st.markdown(
                        '<div class="history-session-heading">'
                        f"<strong>Session #{int(session_id)}</strong>"
                        f"<span>{exercises_count} exercises · {total_sets} sets{linked_workout}</span></div>",
                        unsafe_allow_html=True,
                    )
                    with st.container(
                        key=f"history_session_actions_{session_id}",
                        horizontal=True,
                        width="content",
                        wrap=True,
                        gap="small",
                    ):
                        if st.button(
                            "Edit plan link" if current else "Link to plan",
                            key=f"history_session_link_{session_id}",
                            icon=":material/check_circle:" if current else ":material/link:",
                            disabled=not link_ready,
                            help=(
                                f"{current['plan_name']} · {current['scheduled_date']:%d %b %Y}. "
                                "Change or remove this link."
                                if current
                                else "Assign this session to a planned workout."
                            )
                            if link_ready
                            else "Plan links are currently unavailable.",
                        ):
                            st.session_state.pop(DATA_SETTINGS_KEY, None)
                            st.session_state.pop(SESSION_TOOLS_KEY, None)
                            st.session_state[SESSION_LINK_KEY] = (
                                int(session_id),
                                session_date.date(),
                            )
                        if st.button(
                            "Session tools",
                            key=f"history_session_tools_{session_id}",
                            icon=":material/tune:",
                            type="primary",
                            help="Edit sets, load details and replacements, or delete this session.",
                        ):
                            st.session_state.pop(DATA_SETTINGS_KEY, None)
                            st.session_state.pop(SESSION_LINK_KEY, None)
                            st.session_state[SESSION_TOOLS_KEY] = (
                                int(session_id),
                                session_date.date(),
                            )
                rows = []
                for position, (_, ex_df) in enumerate(
                    session_df.groupby(group_key, sort=False), start=1
                ):
                    exercise = ex_df["exercise_name"].iloc[0]
                    shared_load = _shared_load_description(ex_df)
                    load_detail = f"<span>{escape(shared_load)}</span>" if shared_load else ""
                    rows.append(
                        '<div class="plan-reference-row history-exercise">'
                        f'<span class="plan-exercise-number">{position:02d}</span>'
                        '<div class="plan-reference-name">'
                        f"<strong>{escape(str(exercise))}</strong>"
                        f"<span>{len(ex_df)} sets</span>{load_detail}</div>"
                        '<div class="history-exercise-results">'
                        f"{_set_results(ex_df, shared_load=shared_load)}</div></div>"
                    )
                st.markdown(
                    '<div class="plan-exercise-list history-exercise-list" tabindex="0" '
                    'role="region" aria-label="Recorded exercises and sets. Scroll horizontally to see all results.">'
                    '<div class="history-exercise-list-content">' + "".join(rows) + "</div></div>",
                    unsafe_allow_html=True,
                )
        pending = st.session_state.get(SESSION_LINK_KEY)
        tools = st.session_state.get(SESSION_TOOLS_KEY)
        if pending and pending[0] in set(df["session_id"]):
            session_plan_link_dialog(self.dm, *pending)
        elif pending:
            st.session_state.pop(SESSION_LINK_KEY, None)
        if tools and tools[0] in set(df["session_id"]):
            session_tools_dialog(self.dm, *tools, self.exercise_names)
        elif tools:
            st.session_state.pop(SESSION_TOOLS_KEY, None)


def _format_seconds(value: int | float) -> str:
    seconds = int(value)
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}:{remaining_seconds:02d}"
    return f"{seconds}s"
