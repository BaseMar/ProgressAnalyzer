"""Readable weekly reference plans with one workout edited at a time."""
from collections import Counter
from datetime import date, timedelta
from html import escape
import logging
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from data_manager import DataManager
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft
from ui.utils.plan_editor import WEEKDAYS
from ui.utils.ui_helpers import page_title, section_header

logger = logging.getLogger(__name__)


class TrainingPlanView:
    def __init__(self, exercises, data_manager=None):
        self.dm = data_manager if data_manager is not None else DataManager()
        counts = Counter(item.name for item in exercises)
        self.labels = {item.exercise_id: item.name + (f" · #{item.exercise_id}" if counts[item.name] > 1 else "")
                       for item in sorted(exercises, key=lambda item: item.name.casefold())}

    def render(self):
        page_title("Reference data", "Training Plan")
        st.caption("Define the weekly reference used to analyse your workout logs.")
        try:
            if not self.dm.training_plan_storage_ready():
                st.info("Training plans are not available yet. Database setup needs to be completed.")
                return
            plans = {plan.plan_id: plan for plan in self.dm.load_training_plans()}
        except SQLAlchemyError:
            logger.exception("Unable to load training plans")
            st.error("Training plans could not be loaded. Please try again.")
            return
        if not self.labels:
            st.info("Add exercises to the catalog before creating a plan.")
            return
        if "plan_saved_notice" in st.session_state:
            st.success(st.session_state.pop("plan_saved_notice"))
        if "plan_next_selection" in st.session_state:
            st.session_state["training_plan_picker"] = st.session_state.pop("plan_next_selection")
        selected = st.selectbox("Your plans", [None, *plans], index=1 if plans else 0, key="training_plan_picker",
                                format_func=lambda value: "Create a new plan" if value is None else plans[value].draft.name)
        source = plans.get(selected)
        if source:
            st.caption(f"Version {source.version_number} · from {source.draft.effective_from:%d %b %Y}")
            self._overview(source.draft, source.version_id)
        if source is None or st.toggle("Edit as a new version", key=f"plan_edit_{source.version_id}"):
            self._render_editor(source)
        if source:
            self._render_history(source.plan_id)

    def _overview(self, draft, version_id):
        cards = []
        for day in sorted(draft.days, key=lambda item: item.weekday):
            cards.append('<div class="plan-week-card">'
                         f'<span>{WEEKDAYS[day.weekday]}</span><strong>{escape(day.name)}</strong>'
                         f'<small>{len(day.exercises)} exercises · {sum(item.set_count for item in day.exercises)} sets</small></div>')
        st.markdown('<div class="plan-week-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
        with st.expander("Reference exercises"):
            index = st.selectbox("Workout", range(len(draft.days)), key=f"reference_workout_{version_id}",
                                 format_func=lambda value: f'{WEEKDAYS[draft.days[value].weekday]} · {draft.days[value].name}')
            for position, item in enumerate(draft.days[index].exercises, start=1):
                rir = f" · RIR {item.target_rir}" if item.target_rir is not None else ""
                st.markdown('<div class="plan-reference-row">'
                            f'<span>{position:02d} · {escape(self.labels.get(item.exercise_id, "Unknown exercise"))}</span>'
                            f'<strong>{item.set_count} × {item.target_min}–{item.target_max} {item.target_unit}{rir}</strong></div>', unsafe_allow_html=True)

    @staticmethod
    def _exercise(item=None, uid=0):
        return dict(uid=uid, exercise_id=item.exercise_id if item else None,
                    sets=item.set_count if item else 3, minimum=item.target_min if item else 6,
                    maximum=item.target_max if item else 10, unit=item.target_unit if item else "reps",
                    rir=item.target_rir if item else None, increment=item.weight_increment if item else None)

    def _day(self, day=None, uid=0):
        exercises = [self._exercise(item, index) for index, item in enumerate(day.exercises)] if day else [self._exercise()]
        return dict(uid=uid, name=day.name if day else "", weekday=day.weekday if day else 0,
                    exercises=exercises, next_exercise=len(exercises))

    @staticmethod
    def _capture(scope, store):
        # Capture before switching cards: Streamlit cleans up hidden widgets.
        for day in store["days"]:
            prefix = f'{scope}_day_{day["uid"]}'
            for field in ("name", "weekday"):
                if f"{prefix}_{field}" in st.session_state:
                    day[field] = st.session_state[f"{prefix}_{field}"]
            for exercise in day["exercises"]:
                for field in ("exercise_id", "sets", "minimum", "maximum", "unit", "rir", "increment"):
                    key = f'{prefix}_ex_{exercise["uid"]}_{field}'
                    if key in st.session_state:
                        exercise[field] = st.session_state[key]

    def _render_editor(self, source):
        scope = f"plan_editor_{source.version_id if source else 'new'}"
        store_key = f"{scope}_draft"
        if store_key not in st.session_state:
            days = [self._day(day, index) for index, day in enumerate(source.draft.days)] if source else [self._day()]
            st.session_state[store_key] = dict(days=days, next_day=len(days))
        store = st.session_state[store_key]
        self._capture(scope, store)
        section_header("Edit reference plan" if source else "New reference plan")
        minimum = max(date.today(), source.draft.effective_from + timedelta(days=1)) if source else None
        with st.container(key="training_plan_details"):
            left, right = st.columns([2, 1])
            name = left.text_input("Plan name", value=store.get("name", source.draft.name if source else ""), max_chars=120,
                                   placeholder="e.g. Upper / Lower", key=f"{scope}_name")
            start = right.date_input("Applies from", value=store.get("start", minimum or date.today()), min_value=minimum, key=f"{scope}_start")
            if source:
                st.caption("Saving creates a new version; previous targets remain in history.")
        store["name"], store["start"] = name, start
        action = None
        if store["days"]:
            ids = [day["uid"] for day in store["days"]]
            if "select_next" in store:
                st.session_state[f"{scope}_active_day"] = store.pop("select_next")
            day_id = st.selectbox("Workout to edit", ids, key=f"{scope}_active_day",
                                  format_func=lambda value: next(f'{WEEKDAYS[day["weekday"]]} · {day["name"] or "Untitled workout"}' for day in store["days"] if day["uid"] == value))
            day = next(item for item in store["days"] if item["uid"] == day_id)
            prefix = f"{scope}_day_{day_id}"
            with st.container(key="training_workout_editor"):
                left, right = st.columns([2, 1])
                left.text_input("Workout name", value=day["name"], placeholder="e.g. Upper A", max_chars=120, key=f"{prefix}_name")
                right.selectbox("Planned weekday", range(7), index=day["weekday"], format_func=lambda value: WEEKDAYS[value], key=f"{prefix}_weekday")
                for index, item in enumerate(day["exercises"]):
                    ex_prefix = f'{prefix}_ex_{item["uid"]}'
                    with st.container(key=f'plan_exercise_{day_id}_{item["uid"]}'):
                        title, up, down, remove = st.columns([5, 1, 1, 1])
                        title.markdown(f'<div class="plan-workout-heading">Exercise {index + 1:02d}</div>', unsafe_allow_html=True)
                        if up.button("↑", key=f"{ex_prefix}_up", help="Move exercise up", disabled=index == 0):
                            action = ("move", day_id, index, -1)
                        if down.button("↓", key=f"{ex_prefix}_down", help="Move exercise down", disabled=index == len(day["exercises"]) - 1):
                            action = ("move", day_id, index, 1)
                        if remove.button("×", key=f"{ex_prefix}_remove", help="Remove exercise"):
                            action = ("remove_exercise", day_id, item["uid"])
                        options = [None, *self.labels]
                        st.selectbox("Exercise", options, index=options.index(item["exercise_id"]),
                                     format_func=lambda value: "Choose an exercise" if value is None else self.labels[value], key=f"{ex_prefix}_exercise_id")
                        sets, lower, upper, unit = st.columns(4)
                        sets.number_input("Sets", min_value=1, value=item["sets"], step=1, key=f"{ex_prefix}_sets")
                        lower.number_input("Minimum", min_value=1, value=item["minimum"], step=1, key=f"{ex_prefix}_minimum")
                        upper.number_input("Maximum", min_value=1, value=item["maximum"], step=1, key=f"{ex_prefix}_maximum")
                        unit.selectbox("Measure", ["reps", "seconds"], index=0 if item["unit"] == "reps" else 1, key=f"{ex_prefix}_unit")
                        with st.expander("Optional RIR target"):
                            st.number_input("Target RIR", min_value=0, value=item["rir"], step=1, key=f"{ex_prefix}_rir")
                add, remove = st.columns(2)
                if add.button("Add exercise", key=f"{prefix}_add_exercise", icon=":material/add:"):
                    action = ("add_exercise", day_id)
                if remove.button("Remove workout", key=f"{prefix}_remove"):
                    action = ("remove_day", day_id)
        self._capture(scope, store)
        if action:
            day = next(item for item in store["days"] if item["uid"] == action[1])
            if action[0] == "move":
                a, b = action[2], action[2] + action[3]
                day["exercises"][a], day["exercises"][b] = day["exercises"][b], day["exercises"][a]
            elif action[0] == "remove_exercise":
                day["exercises"] = [item for item in day["exercises"] if item["uid"] != action[2]]
            elif action[0] == "add_exercise":
                day["exercises"].append(self._exercise(uid=day["next_exercise"]))
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
        st.caption("Edit one workout at a time. All workouts are saved together below.")
        if st.button("Save new version" if source else "Save plan", key=f"{scope}_save", type="primary"):
            try:
                days = []
                for day in store["days"]:
                    exercises = []
                    for item in day["exercises"]:
                        if item["exercise_id"] not in self.labels:
                            raise ValueError(f'{day["name"] or "Workout"}: choose an exercise')
                        exercises.append(PlannedExercise(item["exercise_id"], item["sets"], item["minimum"], item["maximum"], item["unit"], item["rir"], item["increment"]))
                    days.append(TrainingDay(day["name"].strip(), day["weekday"], tuple(exercises)))
                saved = self.dm.save_training_plan(TrainingPlanDraft(name.strip(), start, tuple(days)), plan_id=source.plan_id if source else None)
            except ValueError as exc:
                st.error(str(exc))
                return
            except SQLAlchemyError:
                logger.exception("Unable to save plan")
                st.error("The plan could not be saved. Your draft is still here.")
                return
            st.session_state["plan_saved_notice"] = f"Saved {saved.draft.name} · version {saved.version_number}."
            st.session_state["plan_next_selection"] = saved.plan_id
            st.rerun()

    def _render_history(self, plan_id):
        with st.expander("Version history"):
            try:
                history = self.dm.load_training_plan_versions(plan_id)
            except SQLAlchemyError:
                st.error("Version history could not be loaded.")
                return
            if len(history) < 2:
                st.caption("No earlier versions.")
                return
            index = st.selectbox("Earlier version", range(len(history) - 2, -1, -1), key=f"plan_history_{plan_id}",
                                 format_func=lambda value: f'Version {history[value].version_number} · from {history[value].draft.effective_from:%d %b %Y}')
            self._overview(history[index].draft, history[index].version_id)
