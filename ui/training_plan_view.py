"""Readable weekly reference plans with one workout edited at a time."""

import logging
from collections import Counter
from datetime import date, timedelta
from html import escape

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from models.training_plan import (
    PlannedExercise,
    ProgressionSettings,
    TrainingDay,
    TrainingPlanDraft,
)
from ui.utils.active_plan import select_active_plan
from ui.utils.plan_editor import WEEKDAYS, capture_draft, capture_plan_drafts
from ui.utils.ui_helpers import page_title, section_header

logger = logging.getLogger(__name__)


def _set_plan_mode(create, version_id=None):
    capture_plan_drafts()
    st.session_state["plan_create_mode"] = create
    st.session_state["plan_editing_version"] = version_id


class TrainingPlanView:
    def __init__(self, exercises, data_manager=None):
        self.dm = data_manager if data_manager is not None else DataManager()
        counts = Counter(item.name for item in exercises)
        self.labels = {
            item.exercise_id: item.name
            + (f" · #{item.exercise_id}" if counts[item.name] > 1 else "")
            for item in sorted(exercises, key=lambda item: item.name.casefold())
        }

    def render(self):
        page_title("Plan", "Your training plan")
        try:
            if not self.dm.training_plan_storage_ready():
                st.info(
                    "Training plans are not available yet. Database setup needs to be completed."
                )
                return
            plans = {plan.plan_id: plan for plan in self.dm.load_training_plans()}
        except SQLAlchemyError:
            logger.exception("Unable to load training plans")
            st.error("Training plans could not be loaded. Please try again.")
            return
        if not self.labels:
            st.info("Add exercises to the catalog before creating a plan.")
            return
        if st.session_state.pop("plan_deleted", False):
            for key in ("adherence_plan", "active_plan_id", "plan_next_selection"):
                st.session_state.pop(key, None)
            st.session_state["plan_create_mode"] = not plans
            st.session_state["plan_editing_version"] = None
        if "plan_saved_notice" in st.session_state:
            st.success(st.session_state.pop("plan_saved_notice"))
        if "plan_next_selection" in st.session_state:
            st.session_state["adherence_plan"] = st.session_state.pop("plan_next_selection")
            st.session_state["active_plan_id"] = st.session_state["adherence_plan"]
            st.session_state["plan_create_mode"] = False
        create = st.session_state.get("plan_create_mode", not plans)
        with st.container(key="plan_main_actions"):
            actions = st.columns(
                [3, 1.3, 1.3] if create else [3, 1.3, 1.3, 1.3],
                vertical_alignment="bottom",
            )
            selection, new, edit = actions[:3]
            with selection:
                if create:
                    st.markdown(
                        '<div class="plan-mode-label">New plan<span>Unsaved draft</span></div>',
                        unsafe_allow_html=True,
                    )
                    selected = None
                else:
                    selected = select_active_plan(plans.values())
            source = None if create else plans.get(selected)
            editing = (
                source is None or st.session_state.get("plan_editing_version") == source.version_id
            )
            if not create:
                new.button(
                    "Create a new plan",
                    key="plan_create_new",
                    width="stretch",
                    icon=":material/add:",
                    on_click=_set_plan_mode,
                    args=(True,),
                )
            if create and plans:
                edit.button(
                    "Back to saved plans",
                    key="plan_back_to_saved",
                    width="stretch",
                    on_click=_set_plan_mode,
                    args=(False,),
                )
            elif source:
                edit.button(
                    "Back to plan" if editing else "Edit plan",
                    key=f"plan_edit_{source.version_id}",
                    width="stretch",
                    type="secondary" if editing else "primary",
                    icon=":material/arrow_back:" if editing else ":material/edit:",
                    on_click=_set_plan_mode,
                    args=(False, None if editing else source.version_id),
                )
                with actions[3]:
                    self._render_delete(source)
        if source and not editing:
            self._plan_summary(source)
            self._overview(source.draft, source.version_id)
        if editing:
            self._render_editor(source)
        if source and not editing:
            self._render_history(source.plan_id)

    def _render_delete(self, source):
        with st.popover("Delete plan", icon=":material/delete:", width="stretch"):
            st.warning(
                f'Delete "{source.draft.name}" and all its versions? '
                "This permanently removes the plan and its workout assignments. "
                "Recorded workouts and sets will remain in History."
            )
            confirmed = st.checkbox(
                "I want to permanently delete this plan",
                key=f"plan_delete_confirm_{source.plan_id}",
            )
            if not st.button(
                "Delete plan",
                key=f"plan_delete_{source.plan_id}",
                icon=":material/delete:",
                disabled=not confirmed,
            ):
                return
            try:
                history = self.dm.load_training_plan_versions(source.plan_id)
                deleted = self.dm.delete_training_plan(source.plan_id)
            except SQLAlchemyError:
                logger.exception("Unable to delete training plan")
                st.error("The plan could not be deleted. Please try again.")
                return
            version_ids = {version.version_id for version in history}
            prefixes = tuple(f"plan_editor_{version_id}_" for version_id in version_ids)
            for key in list(st.session_state):
                if prefixes and key.startswith(prefixes):
                    del st.session_state[key]
            st.session_state["plan_deleted"] = True
            st.session_state["plan_saved_notice"] = (
                "Plan deleted. Recorded workouts and sets have been kept."
                if deleted
                else "This plan has already been deleted."
            )
            st.rerun()

    @staticmethod
    def _plan_summary(source):
        draft = source.draft
        block = (
            f"<span>{draft.progression.block_weeks}-week block · final week deload</span>"
            if draft.progression
            else ""
        )
        st.markdown(
            '<div class="plan-summary">'
            '<div class="plan-summary-title">'
            f"<h2>{escape(draft.name)}</h2><span>Version {source.version_number} · "
            f"from {draft.effective_from:%d %b %Y}</span></div>"
            '<div class="plan-summary-stats">'
            f"<span><strong>{len(draft.days)}</strong> workouts / week</span>"
            f"<span><strong>{sum(len(day.exercises) for day in draft.days)}</strong> exercises</span>"
            f"<span><strong>{sum(item.set_count for day in draft.days for item in day.exercises)}</strong> sets / week</span>"
            f"</div>{block}</div>",
            unsafe_allow_html=True,
        )

    def _overview(self, draft, version_id):
        section_header("Weekly schedule", first=True)
        cards = []
        for day in sorted(draft.days, key=lambda item: item.weekday):
            cards.append(
                '<div class="plan-week-card">'
                f"<span>{WEEKDAYS[day.weekday]}</span><strong>{escape(day.name)}</strong>"
                f"<small>{len(day.exercises)} exercises · {sum(item.set_count for item in day.exercises)} sets</small></div>"
            )
        st.markdown(
            '<div class="plan-week-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True
        )
        section_header("Workout details")
        index = st.selectbox(
            "Workout",
            range(len(draft.days)),
            key=f"reference_workout_{version_id}",
            format_func=lambda value: (
                f"{WEEKDAYS[draft.days[value].weekday]} · {draft.days[value].name}"
            ),
        )
        rows = []
        for position, item in enumerate(draft.days[index].exercises, start=1):
            rir = f"RIR {item.target_rir}" if item.target_rir is not None else ""
            weight_step = (
                f"{item.weight_increment:g} kg step" if item.weight_increment is not None else ""
            )
            detail = " · ".join(filter(None, (rir, weight_step)))
            rows.append(
                '<div class="plan-reference-row">'
                f'<span class="plan-exercise-number">{position:02d}</span>'
                '<div class="plan-reference-name">'
                f"<strong>{escape(self.labels.get(item.exercise_id, 'Unknown exercise'))}</strong>"
                f"<span>{escape(detail)}</span></div>"
                f'<strong class="plan-reference-target">{self._target_label(item.set_count, item.target_min, item.target_max, item.target_unit)}</strong></div>'
            )
        st.markdown(
            '<div class="plan-exercise-list">' + "".join(rows) + "</div>", unsafe_allow_html=True
        )

    @staticmethod
    def _target_label(sets, minimum, maximum, unit):
        quantity = str(minimum) if minimum == maximum else f"{minimum}–{maximum}"
        return f"{sets} × {quantity} {unit}"

    @staticmethod
    def _exercise(item=None, uid=0):
        return dict(
            uid=uid,
            exercise_id=item.exercise_id if item else None,
            sets=item.set_count if item else 3,
            minimum=item.target_min if item else 6,
            maximum=item.target_max if item else 10,
            unit=item.target_unit if item else "reps",
            rir=item.target_rir if item else None,
            increment=item.weight_increment if item else None,
            history_key=item.history_key if item else None,
        )

    def _day(self, day=None, uid=0):
        exercises = (
            [self._exercise(item, index) for index, item in enumerate(day.exercises)]
            if day
            else [self._exercise()]
        )
        return dict(
            uid=uid,
            name=day.name if day else "",
            weekday=day.weekday if day else 0,
            exercises=exercises,
            next_exercise=len(exercises),
        )

    @staticmethod
    def _capture(scope, store):
        capture_draft(scope, store)

    def _render_editor(self, source):
        scope = f"plan_editor_{source.version_id if source else 'new'}"
        store_key = f"{scope}_draft"
        if store_key not in st.session_state:
            days = (
                [self._day(day, index) for index, day in enumerate(source.draft.days)]
                if source
                else [self._day()]
            )
            st.session_state[store_key] = dict(days=days, next_day=len(days))
        store = st.session_state[store_key]
        self._capture(scope, store)
        section_header("Plan details", first=True)
        minimum = (
            max(date.today(), source.draft.effective_from + timedelta(days=1)) if source else None
        )
        with st.container(key="training_plan_details"):
            left, right = st.columns([2, 1])
            name = left.text_input(
                "Plan name",
                value=store.get("name", source.draft.name if source else ""),
                max_chars=120,
                placeholder="e.g. Upper / Lower",
                key=f"{scope}_name",
            )
            start = right.date_input(
                "Applies from",
                value=store.get("start", minimum or date.today()),
                min_value=minimum,
                key=f"{scope}_start",
            )
            if source:
                st.caption("Saving creates a new version; previous targets remain in history.")
        store["name"], store["start"] = name, start
        section_header("Weekly routine")
        action = self._render_workout_editor(scope, store)
        self._capture(scope, store)
        if action:
            day = next(item for item in store["days"] if item["uid"] == action[1])
            if action[0] == "move":
                a, b = action[2], action[2] + action[3]
                day["exercises"][a], day["exercises"][b] = day["exercises"][b], day["exercises"][a]
            elif action[0] == "remove_exercise":
                day["exercises"] = [item for item in day["exercises"] if item["uid"] != action[2]]
                if day["exercises"]:
                    day["select_exercise_next"] = day["exercises"][0]["uid"]
            elif action[0] == "add_exercise":
                day["exercises"].append(self._exercise(uid=day["next_exercise"]))
                day["select_exercise_next"] = day["next_exercise"]
                day["next_exercise"] += 1
            else:
                store["days"].remove(day)
                if store["days"]:
                    store["select_next"] = store["days"][0]["uid"]
            st.rerun()
        if st.button("Add workout", key=f"{scope}_add", icon=":material/add:"):
            uid = store["next_day"]
            store["days"].append(self._day(uid=uid))
            store["next_day"] += 1
            store["select_next"] = uid
            st.rerun()
        section_header("Training block")
        saved_settings = source.draft.progression if source else None
        with st.expander("Deload schedule"):
            enabled = (
                True
                if saved_settings
                else st.checkbox(
                    "Configure training block",
                    value=store.get("progression_enabled", False),
                    key=f"{scope}_progression_enabled",
                )
            )
            store["progression_enabled"] = enabled
            if enabled:
                left, right = st.columns(2)
                block_start = left.date_input(
                    "Block starts on",
                    value=store.get(
                        "block_start",
                        saved_settings.block_start
                        if saved_settings
                        else source.draft.effective_from
                        if source
                        else start,
                    ),
                    key=f"{scope}_block_start",
                )
                weeks = store.get(
                    "block_weeks", saved_settings.block_weeks if saved_settings else 7
                )
                block_weeks = right.selectbox(
                    "Block length (weeks)",
                    [6, 7, 8],
                    index=[6, 7, 8].index(weeks),
                    key=f"{scope}_block_weeks",
                )
                store["block_start"], store["block_weeks"] = block_start, block_weeks
                st.caption("The block repeats from this date; its final week is deload.")
        section_header("Save plan")
        with st.container(key="training_plan_save"):
            summary, save = st.columns([3, 1], vertical_alignment="center")
            summary.markdown(
                '<div class="plan-save-summary"><strong>'
                + escape(name.strip() or "Untitled plan")
                + f"</strong><span>{len(store['days'])} workouts · "
                + f"{sum(len(day['exercises']) for day in store['days'])} exercises"
                + "</span></div>",
                unsafe_allow_html=True,
            )
            save_requested = save.button(
                "Save new version" if source else "Save plan",
                key=f"{scope}_save",
                type="primary",
                icon=":material/check:",
                width="stretch",
            )
            st.caption("Saves all workouts. Your draft stays available until then.")
        if save_requested:
            try:
                days = []
                for day in store["days"]:
                    exercises = []
                    for item in day["exercises"]:
                        if item["exercise_id"] not in self.labels:
                            raise ValueError(f"{day['name'] or 'Workout'}: choose an exercise")
                        exercises.append(
                            PlannedExercise(
                                item["exercise_id"],
                                item["sets"],
                                item["minimum"],
                                item["maximum"],
                                item["unit"],
                                item["rir"],
                                item["increment"],
                                history_key=item.get("history_key"),
                            )
                        )
                    days.append(TrainingDay(day["name"].strip(), day["weekday"], tuple(exercises)))
                progression = (
                    ProgressionSettings(store["block_start"], store["block_weeks"])
                    if store["progression_enabled"]
                    else None
                )
                saved = self.dm.save_training_plan(
                    TrainingPlanDraft(name.strip(), start, tuple(days), progression),
                    plan_id=source.plan_id if source else None,
                )
            except ValueError as exc:
                st.error(str(exc))
                return
            except SQLAlchemyError:
                logger.exception("Unable to save plan")
                st.error("The plan could not be saved. Your draft is still here.")
                return
            st.session_state["plan_saved_notice"] = (
                f"Saved {saved.draft.name} · version {saved.version_number}."
            )
            st.session_state["plan_next_selection"] = saved.plan_id
            st.rerun()

    def _render_workout_editor(self, scope, store):
        if not store["days"]:
            st.info("Add a workout to start building your week.")
            return None
        ids = [day["uid"] for day in store["days"]]
        day_key = f"{scope}_active_day"
        selected_day = store.pop(
            "select_next", st.session_state.get(day_key, store.get("selected_day"))
        )
        # The client stores option labels. Resend the selected ID when edits rename them.
        st.session_state[day_key] = selected_day if selected_day in ids else ids[0]
        day_labels = {
            day[
                "uid"
            ]: f"{index + 1:02d} · {WEEKDAYS[day['weekday']]} · {day['name'] or 'Untitled workout'}"
            for index, day in enumerate(store["days"])
        }
        action = None
        with st.container(key="plan_editor_workspace"):
            navigation, details = st.columns([1, 1.7], gap="large")
            with navigation, st.container(key="training_workout_editor"):
                day_id = st.selectbox(
                    "Workout to edit",
                    ids,
                    key=day_key,
                    format_func=day_labels.__getitem__,
                )
                day = next(item for item in store["days"] if item["uid"] == day_id)
                prefix = f"{scope}_day_{day_id}"
                st.text_input(
                    "Workout name",
                    value=day["name"],
                    placeholder="e.g. Upper A",
                    max_chars=120,
                    key=f"{prefix}_name",
                )
                st.selectbox(
                    "Planned weekday",
                    range(7),
                    index=day["weekday"],
                    format_func=lambda value: WEEKDAYS[value],
                    key=f"{prefix}_weekday",
                )
                st.markdown(
                    '<div class="plan-panel-heading" role="heading" aria-level="3">Exercises</div>',
                    unsafe_allow_html=True,
                )
                selected_exercise = None
                if day["exercises"]:
                    exercise_ids = [item["uid"] for item in day["exercises"]]
                    exercise_key = f"{prefix}_active_exercise"
                    selected_exercise = day.pop(
                        "select_exercise_next",
                        st.session_state.get(exercise_key, day.get("selected_exercise")),
                    )
                    st.session_state[exercise_key] = (
                        selected_exercise if selected_exercise in exercise_ids else exercise_ids[0]
                    )
                    with st.container(key="plan_exercise_navigation"):
                        exercise_labels = {
                            item[
                                "uid"
                            ]: f"{index + 1:02d} · {self.labels.get(item['exercise_id'], 'Choose an exercise')}"
                            for index, item in enumerate(day["exercises"])
                        }
                        selected_exercise = st.radio(
                            "Exercise to edit",
                            exercise_ids,
                            key=exercise_key,
                            label_visibility="collapsed",
                            width="stretch",
                            format_func=exercise_labels.__getitem__,
                        )
                else:
                    st.caption("No exercises yet.")
                if st.button(
                    "Add exercise",
                    key=f"{prefix}_add_exercise",
                    icon=":material/add:",
                    width="stretch",
                ):
                    action = ("add_exercise", day_id)
                if st.button(
                    "Remove workout",
                    key=f"{prefix}_remove",
                    icon=":material/delete:",
                    width="stretch",
                ):
                    action = ("remove_day", day_id)
            with details:
                if selected_exercise is None:
                    with st.container(key="plan_empty_exercise"):
                        st.markdown(
                            '<div class="plan-empty-state"><span class="plan-panel-heading">Exercise targets</span>'
                            "<strong>Build this workout</strong>"
                            "<p>Add an exercise to set its repetitions, time and reserve.</p></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    index, item = next(
                        (index, item)
                        for index, item in enumerate(day["exercises"])
                        if item["uid"] == selected_exercise
                    )
                    exercise_action = self._render_exercise_editor(scope, store, day, index, item)
                    action = exercise_action or action
        return action

    def _render_exercise_editor(self, scope, store, day, index, item):
        day_id = day["uid"]
        prefix = f"{scope}_day_{day_id}_ex_{item['uid']}"
        action = None
        with st.container(key="training_exercise_editor"):
            with st.container(key=f"{prefix}_controls"):
                title, up, down, remove = st.columns([5, 1, 1, 1], vertical_alignment="center")
                title.markdown(
                    f'<div class="plan-panel-heading" role="heading" aria-level="3">Exercise {index + 1:02d}</div>',
                    unsafe_allow_html=True,
                )
                if up.button(
                    "↑",
                    key=f"{prefix}_up",
                    help="Move exercise up",
                    disabled=index == 0,
                ):
                    action = ("move", day_id, index, -1)
                if down.button(
                    "↓",
                    key=f"{prefix}_down",
                    help="Move exercise down",
                    disabled=index == len(day["exercises"]) - 1,
                ):
                    action = ("move", day_id, index, 1)
                if remove.button("×", key=f"{prefix}_remove", help="Remove exercise"):
                    action = ("remove_exercise", day_id, item["uid"])
            options = [None, *self.labels]
            st.selectbox(
                "Exercise",
                options,
                index=options.index(item["exercise_id"]),
                format_func=lambda value: (
                    "Choose an exercise" if value is None else self.labels[value]
                ),
                key=f"{prefix}_exercise_id",
            )
            with st.container(key="plan_target_fields"):
                sets, unit = st.columns(2)
                sets.number_input(
                    "Sets", min_value=1, value=item["sets"], step=1, key=f"{prefix}_sets"
                )
                unit.selectbox(
                    "Measure",
                    ["reps", "seconds"],
                    index=0 if item["unit"] == "reps" else 1,
                    key=f"{prefix}_unit",
                )
                lower, upper = st.columns(2)
                lower.number_input(
                    "Minimum", min_value=1, value=item["minimum"], step=1, key=f"{prefix}_minimum"
                )
                upper.number_input(
                    "Maximum", min_value=1, value=item["maximum"], step=1, key=f"{prefix}_maximum"
                )
                rir, step = st.columns(2)
                rir.number_input(
                    "Target RIR",
                    min_value=0,
                    value=item["rir"],
                    step=1,
                    key=f"{prefix}_rir",
                    help="Repetitions in reserve after a set. Leave blank if unknown.",
                )
                step.number_input(
                    "Weight step (kg)",
                    min_value=0.01,
                    value=float(item["increment"]) if item["increment"] is not None else None,
                    step=0.25,
                    format="%.2f",
                    key=f"{prefix}_increment",
                    help="Smallest available increase, using the same weight convention as your log. Leave blank if unknown.",
                )
            self._capture(scope, store)
            extra = " · ".join(
                filter(
                    None,
                    (
                        f"RIR {item['rir']}" if item["rir"] is not None else "",
                        f"{item['increment']:g} kg step" if item["increment"] is not None else "",
                    ),
                )
            )
            st.markdown(
                '<div class="plan-target-preview"><span>Target per workout</span>'
                f"<strong>{self._target_label(item['sets'], item['minimum'], item['maximum'], item['unit'])}</strong>"
                f"<small>{escape(extra)}</small></div>",
                unsafe_allow_html=True,
            )
        return action

    def _render_history(self, plan_id):
        section_header("Version history")
        with st.expander("Previous versions"):
            try:
                history = self.dm.load_training_plan_versions(plan_id)
            except SQLAlchemyError:
                st.error("Version history could not be loaded.")
                return
            if len(history) < 2:
                st.caption("No earlier versions.")
                return
            index = st.selectbox(
                "Earlier version",
                range(len(history) - 2, -1, -1),
                key=f"plan_history_{plan_id}",
                format_func=lambda value: (
                    f"Version {history[value].version_number} · from {history[value].draft.effective_from:%d %b %Y}"
                ),
            )
            self._overview(history[index].draft, history[index].version_id)
