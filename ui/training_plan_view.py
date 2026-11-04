"""Training-plan editor and version history, backed by snapshot storage."""

from datetime import date, timedelta
from html import escape
import logging

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from models.exercise import Exercise
from models.training_plan import TrainingPlanVersion
from ui.utils.plan_editor import WEEKDAYS, draft_from_editor, exercise_rows
from ui.utils.ui_helpers import page_title, section_header

logger = logging.getLogger(__name__)


class TrainingPlanView:
    def __init__(self, exercises: list[Exercise], data_manager=None):
        self.dm = data_manager if data_manager is not None else DataManager()
        self.labels = {item.exercise_id: f"{item.name} · #{item.exercise_id}" for item in sorted(exercises, key=lambda item: item.name.casefold())}
        self.catalog = {label: exercise_id for exercise_id, label in self.labels.items()}

    def render(self):
        page_title("Your routine", "Training Plan")
        st.caption("Build your weekly routine and set a clear target for every exercise.")
        try:
            if not self.dm.training_plan_storage_ready():
                st.info("Training plans are not available yet. Database setup needs to be completed.")
                return
            saved_plans = self.dm.load_training_plans()
        except SQLAlchemyError:
            logger.exception("Unable to load training plans")
            st.error("Training plans could not be loaded. Please try again.")
            return
        if not self.catalog:
            st.info("Add exercises to your exercise catalog before building a plan.")
            return

        if "plan_saved_notice" in st.session_state:
            st.success(st.session_state.pop("plan_saved_notice"))
        by_id = {plan.plan_id: plan for plan in saved_plans}
        if "plan_next_selection" in st.session_state:
            st.session_state["training_plan_picker"] = st.session_state.pop("plan_next_selection")
        selected = st.selectbox(
            "Your plans", [None, *by_id], key="training_plan_picker",
            format_func=lambda value: "Create a new plan" if value is None else f"{by_id[value].draft.name} · v{by_id[value].version_number}",
        )
        source = by_id.get(selected)
        self._render_editor(source)
        if source:
            self._render_history(source.plan_id)

    def _render_editor(self, source: TrainingPlanVersion | None):
        scope = f"plan_editor_{source.version_id if source else 'new'}"
        seed_days = source.draft.days if source else ()
        state_key = f"{scope}_days"
        if state_key not in st.session_state:
            st.session_state[state_key] = list(range(len(seed_days))) if seed_days else [0]
            st.session_state[f"{scope}_next_day"] = len(st.session_state[state_key])

        section_header("New version" if source else "New plan")
        min_date = max(date.today(), source.draft.effective_from + timedelta(days=1)) if source else None
        with st.container(key="training_plan_details"):
            name_col, date_col = st.columns([2, 1])
            name = name_col.text_input("Plan name", value=source.draft.name if source else "", max_chars=120, placeholder="e.g. Upper / Lower", key=f"{scope}_name")
            start = date_col.date_input("Starts on", value=min_date or date.today(), min_value=min_date, key=f"{scope}_start")
            if source:
                st.caption(f"Saving creates version {source.version_number + 1}. Earlier versions remain available in history.")

        workouts = []
        frames = {}
        remove_id = None
        epoch = st.session_state.get(f"{scope}_table_epoch", 0)
        suffix = f"_r{epoch}" if epoch else ""
        for index, day_id in enumerate(st.session_state[state_key], start=1):
            seed = seed_days[day_id] if day_id < len(seed_days) else None
            prefix = f"{scope}_day_{day_id}"
            with st.container(key=f"training_workout_{day_id}"):
                title_col, remove_col = st.columns([5, 1])
                title_col.markdown(f'<div class="plan-workout-heading">Workout {index:02d}</div>', unsafe_allow_html=True)
                if remove_col.button("Remove", key=f"{prefix}_remove", use_container_width=True):
                    remove_id = day_id
                day_name_col, weekday_col = st.columns([2, 1])
                day_name = day_name_col.text_input("Workout name", value=seed.name if seed else "", placeholder="e.g. Upper A", max_chars=120, key=f"{prefix}_name")
                weekday = weekday_col.selectbox("Weekday", range(7), index=seed.weekday if seed else 0, format_func=lambda value: WEEKDAYS[value], key=f"{prefix}_weekday")
                frame = st.data_editor(
                    st.session_state.get(f"{prefix}_base_frame", exercise_rows(seed, self.labels)),
                    key=f"{prefix}_exercises{suffix}",
                    num_rows="dynamic", hide_index=True, width="stretch",
                    column_config={
                        "Order": st.column_config.NumberColumn("Order", min_value=1, step=1, required=True, help="Set a unique number to change exercise order."),
                        "Exercise": st.column_config.SelectboxColumn("Exercise", options=list(self.catalog), required=True, width="large"),
                        "Sets": st.column_config.NumberColumn("Sets", min_value=1, step=1, default=3, required=True),
                        "From": st.column_config.NumberColumn("From", min_value=1, step=1, default=6, required=True),
                        "To": st.column_config.NumberColumn("To", min_value=1, step=1, default=10, required=True),
                        "Unit": st.column_config.SelectboxColumn("Unit", options=["reps", "seconds"], default="reps", required=True),
                        "RIR": st.column_config.NumberColumn("Target RIR", min_value=0, step=1),
                        "Increment": st.column_config.NumberColumn("Weight step (kg)", min_value=0.01, step=0.5, format="%.2f"),
                    },
                )
                frames[day_id] = frame
                workouts.append((day_name, weekday, frame))

        # Finish rendering every input before rerunning; otherwise Streamlit
        # discards widget state belonging to workouts below the removed card.
        if remove_id is not None:
            self._preserve_tables(scope, frames, epoch)
            st.session_state[state_key].remove(remove_id)
            st.rerun()
        if st.button("Add workout", key=f"{scope}_add", icon=":material/add:"):
            self._preserve_tables(scope, frames, epoch)
            next_id = st.session_state[f"{scope}_next_day"]
            st.session_state[state_key].append(next_id)
            st.session_state[f"{scope}_next_day"] += 1
            st.rerun()
        st.caption("Add or delete exercise rows in the table. Set From / To to your repetition range or seconds. RIR and weight step are optional.")
        if st.button("Save new version" if source else "Save plan", type="primary", key=f"{scope}_save", icon=":material/save:"):
            try:
                draft = draft_from_editor(name, start, workouts, self.catalog)
                saved = self.dm.save_training_plan(draft, plan_id=source.plan_id if source else None)
            except ValueError as exc:
                st.error(str(exc))
                return
            except SQLAlchemyError:
                logger.exception("Unable to save training plan")
                st.error("The plan could not be saved. Your draft is still here; please try again.")
                return
            st.session_state["plan_saved_notice"] = f"Saved {saved.draft.name} · version {saved.version_number}."
            st.session_state["plan_next_selection"] = saved.plan_id
            st.rerun()

    @staticmethod
    def _preserve_tables(scope, frames, epoch):
        # Rebase editor deltas on the visible table when changing card structure.
        for day_id, frame in frames.items():
            st.session_state[f"{scope}_day_{day_id}_base_frame"] = frame.copy()
        st.session_state[f"{scope}_table_epoch"] = epoch + 1

    def _render_history(self, plan_id: int):
        section_header("Version history")
        try:
            history = self.dm.load_training_plan_versions(plan_id)
        except SQLAlchemyError:
            logger.exception("Unable to load plan history")
            st.error("Version history could not be loaded. Please try again.")
            return
        for index in range(len(history) - 1, -1, -1):
            version = history[index]
            end = history[index + 1].draft.effective_from - timedelta(days=1) if index + 1 < len(history) else None
            period = f"{version.draft.effective_from:%d %b %Y}" + (f" – {end:%d %b %Y}" if end else " onwards")
            with st.expander(f"Version {version.version_number} · {version.draft.name} · {period}"):
                for day in version.draft.days:
                    st.markdown(f"**{escape(day.name)} · {WEEKDAYS[day.weekday]}**")
                    st.dataframe(exercise_rows(day, self.labels), hide_index=True, width="stretch")
