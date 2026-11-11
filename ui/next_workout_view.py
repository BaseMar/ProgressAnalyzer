"""Compact next-session targets; historical analytics remain separate."""

import logging
from datetime import date, timedelta
from html import escape

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from metrics.recommendation_history import approved_alternatives
from metrics.utils.recommendation_text import goal_summary
from metrics.workout_template import workout_template
from models.training_insights import WorkoutPreview
from ui.manual_start import (
    MANUAL_START_REASONS,
    choose_starting_loads,
    prescription_summary,
    reference_html,
)
from ui.utils.copy_workout import copy_workout
from ui.utils.ui_helpers import section_header

logger = logging.getLogger(__name__)


def recommendation_note(item):
    if item.reason_code in (
        "manual_start",
        "changed_set_count",
        "history_gap",
        "manual_start_selected",
        "reuse_exercise_baseline",
    ):
        return item.reason
    notes = {
        "one_more_rep": "Try one additional total rep in the first set below the ceiling; retain per-set loads and reserve.",
        "upper_range_confirmed": "All sets reached the ceiling at one common load. One complete result is enough: add one equipment step.",
        "equalize_loads": "Bring lighter sets toward the first working load within 10% per set. Raised sets start at the lower rep bound.",
        "minimum_not_met": "Reduce the affected set by one equipment step after the first failure at the minimum.",
        "reduction_step_not_supported": "Choose a lower load for the affected set manually; no positive lower equipment setting is available.",
        "manual_start": "Review the source history and choose the working start manually for this context.",
        "more_time": "Try up to five additional seconds in one set within the time range.",
        "time_ceiling_manual": "Time ceiling reached. Choose a new range or load manually.",
        "confirm_upper_range": "Repeat the upper range with enough reserve before increasing weight.",
        "rir_below_target": "Keep the load: at least one previous set had less reserve than planned.",
        "below_range": "Keep the load and work towards the planned repetition range.",
        "mixed_loads": "Keep each set's logged load; automatic increases need one common working load.",
        "mixed_range": "Some sets exceeded the range while others stayed below its upper bound.",
        "timed_exercise": "Keep the logged load and time range; automatic timed progression is not supported.",
        "bodyweight_load_manual": "Choose additional weight or assistance manually. Keep the displayed rep target; less assistance increases difficulty. Future body mass is not assumed.",
        "unknown_load": "Add the missing body mass or assistance in History before comparing loads.",
        "mixed_load_convention": "The latest sets use different load conventions. Choose the next load manually.",
        "zero_load": "Keep this target; adding external load requires a manual decision.",
        "weight_step_not_supported": "The available weight step is too large for an automatic increase.",
        "scheduled_deload": "Lighter week: same sets and recorded repetitions, 30–40% less load, target RIR 3–4.",
        "resume_after_deload": "Return to the last ordinary loads. Establish progression again in this block.",
        "no_history": "Choose working loads using the recorded results below. Log and link the completed workout to establish a baseline.",
        "no_normal_baseline": "No comparable normal workout is linked in this block. Review any earlier records below and choose working loads manually. Log and link the completed workout to establish a baseline.",
        "reuse_exercise_baseline": "Starting loads from this exercise's history. Use the current range and RIR; adjust the load as needed. A changed workout or prescription needs a new execution before automatic increases.",
        "changed_set_count": "History is available, but the set count changed. Choose loads for the new sets manually.",
        "incomplete_sets": "Review the latest linked workout: its matching working-set count is incomplete.",
        "light_sets": "Light sets remain in history; log the planned ordinary work before increasing the target.",
        "low_effort_sets": "Sets above RIR 5 remain in history and do not establish an ordinary progression target.",
        "missing_rir": "Complete the missing RIR values in the source workout.",
        "missing_target_rir": "Set target RIR in Plan → Progression & RIR.",
        "history_gap": "The last comparable workout is too old. Establish a new baseline.",
        "invalid_values": "Review the source workout's load and RIR values.",
        "deload_load_not_supported": "Choose a deload load manually; this load or equipment step is unsupported.",
        "deload_timed_not_supported": "Choose a timed deload target manually; automatic targets are not supported.",
        "already_recorded": "This workout has already been linked. Select another upcoming workout.",
    }
    if item.reason_code in ("missing_weight_step", "invalid_weight_step"):
        if item.actual_exercise_id != item.planned_exercise_id:
            return "Enter a positive weight step for this alternative in the options above."
        return "Set the available weight step in Plan → Progression & RIR."
    return notes.get(item.reason_code, item.reason)


class NextWorkoutView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.names = exercise_names or {}

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self, plan_id, versions, *, context=None, history=None, as_of=None):
        with st.container(key="next_workout_workspace"):
            as_of = as_of or date.today()
            section_header("Next workout")
            try:
                return self._render(plan_id, versions, history, as_of, context=context)
            except SQLAlchemyError:
                logger.exception("Unable to load next-workout recommendations")
                st.error(
                    "Next-workout targets could not be loaded. Your recorded history is still available."
                )
            except ValueError:
                logger.exception("Next-workout selection is no longer valid")
                st.info(
                    "The plan or workout assignment changed. Refresh this view to select the next workout."
                )

    def _render(self, plan_id, versions, history, as_of, *, context=None):
        if not versions:
            st.info("Save a Training Plan to see the next workout.")
            return
        first = max(as_of, min(version.draft.effective_from for version in versions))
        end = first + timedelta(days=28)
        if context is None:
            context = self.dm.prepare_plan_context(
                plan_id, as_of, end, as_of=as_of, versions=versions
            )
        if context.plan_id != plan_id or context.as_of != as_of:
            raise ValueError("The preview context must use the selected plan and cutoff date")
        slots = sorted(
            (
                item.slot
                for item in context.history.workouts
                if as_of <= item.slot.scheduled_date <= end and item.slot.session_id is None
            ),
            key=lambda slot: (slot.scheduled_date, slot.position, slot.day_id),
        )
        if not slots:
            st.info("All workouts in the upcoming four-week window are already linked.")
            return
        choices = {f"{slot.day_id}:{slot.scheduled_date}": slot for slot in slots}
        selection_key = f"next_workout_{plan_id}"
        if st.session_state.get(selection_key) not in choices:
            st.session_state[selection_key] = next(iter(choices))
        with st.container(key="next_workout_card"):
            selected = st.selectbox(
                "Upcoming workout",
                list(choices),
                key=selection_key,
                format_func=lambda key: (
                    f"{choices[key].scheduled_date:%a, %d %b %Y} · {choices[key].name}"
                ),
            )
            slot = choices[selected]
            prepared = context.prepare_workout(slot.day_id, slot.scheduled_date)
            result = self.dm.recommend_prepared_workout(prepared)
            version = next(version for version in versions if version.version_id == slot.version_id)
            self._heading(slot, result.block, version.draft.progression)
            copy_area = st.container()
            if result.block.phase == "not_started":
                st.info(
                    f"The training block starts on {version.draft.progression.block_start:%d %b %Y}. Select a workout on or after that date."
                )
                return
            if any(item.reason_code == "already_recorded" for item in result.exercises):
                st.info(
                    "This workout was linked while the view was loading. Refresh to select another upcoming workout."
                )
                return
            planned = version.draft.days[slot.position - 1]
            if history is None:
                history = context.history
            alternatives = approved_alternatives(history, slot, planned.exercises, as_of=as_of)
            substitutions, steps = self._alternatives(plan_id, slot, result.exercises, alternatives)
            if substitutions:
                result = self.dm.recommend_prepared_workout(
                    prepared, substitutions=substitutions, replacement_weight_steps=steps
                )
            upcoming = prepared.upcoming
            references = self.dm.load_recommendation_references(
                {
                    item.actual_exercise_id
                    for item in result.exercises
                    if item.reason_code in MANUAL_START_REASONS
                },
                as_of=as_of,
            )
            result = choose_starting_loads(result, upcoming, self.names, references, self.dm)
            prescriptions = {
                target.plan_exercise_id: target.exercise for target in upcoming.targets
            }

            def exercise_card(item):
                return self._exercise(
                    item,
                    prescriptions[item.plan_exercise_id],
                    references.get(item.actual_exercise_id, ()),
                )

            template = workout_template(upcoming, result, self.names)
            with copy_area:
                copy_workout(
                    template, key=f"copy_workout_{plan_id}_{slot.day_id}_{slot.scheduled_date}"
                )
                with st.expander("Copy preview"):
                    st.caption(
                        "Paste into Samsung Notes. After training, enter your actual results and RIR."
                    )
                    st.code(template, language=None, wrap_lines=True)
            st.markdown(
                '<div class="recommendation-list">'
                + "".join(exercise_card(item) for item in result.exercises)
                + "</div>",
                unsafe_allow_html=True,
            )
            return WorkoutPreview(upcoming, result)

    @staticmethod
    def _heading(slot, phase, settings):
        label = {
            "normal": "Normal training",
            "deload": "Deload",
            "unconfigured": "Normal training",
            "not_started": "Before block",
        }[phase.phase]
        st.markdown(
            '<div class="recommendation-heading"><div>'
            f"<span>{slot.scheduled_date:%A, %d %B}</span><strong>{escape(slot.name)}</strong></div>"
            f'<span class="recommendation-phase recommendation-phase--{phase.phase}">{label}</span></div>',
            unsafe_allow_html=True,
        )
        if phase.week is not None:
            st.caption(
                f"Block {phase.cycle} · Week {phase.week} of {settings.block_weeks} · Deload {phase.deload_start:%d %b}–{phase.cycle_end:%d %b}"
            )

    def _alternatives(self, plan_id, slot, recommendations, alternatives):
        substitutions, steps = {}, {}
        if not any(alternatives.values()):
            return substitutions, steps
        scope = f"recommendation_{plan_id}_{slot.day_id}_{slot.scheduled_date}"
        with st.expander("Use a confirmed alternative"):
            st.caption(
                "Choose an alternative previously approved for this workout context. Choices apply to this preview only; confirm the actual replacement after logging the session."
            )
            for position, item in enumerate(recommendations, start=1):
                if not alternatives[position]:
                    continue
                original = item.planned_exercise_id
                options = [original, *sorted(alternatives[position], key=self._name)]
                key = f"{scope}_{item.plan_exercise_id}_exercise"
                if st.session_state.get(key) not in options:
                    st.session_state[key] = original
                actual = st.selectbox(
                    f"Exercise for {self._name(original)} · position {position}",
                    options,
                    key=key,
                    format_func=lambda value, original=original: (
                        self._name(value) + (" (planned)" if value == original else "")
                    ),
                )
                if actual != original:
                    substitutions[item.plan_exercise_id] = actual
            for actual in sorted(set(substitutions.values())):
                value = st.number_input(
                    f"Weight step · {self._name(actual)} (kg)",
                    min_value=0.01,
                    value=None,
                    step=0.25,
                    format="%.2f",
                    placeholder="e.g. 5.00",
                    key=f"{scope}_step_{actual}",
                    help="Smallest available load change on this equipment, using the same weight convention as your logs.",
                )
                if value is not None:
                    steps[actual] = value
        return substitutions, steps

    def _exercise(self, item, planned=None, references=()):
        label = {
            "increase_reps": "Add a rep",
            "increase_time": "Add time",
            "equalize_weight": "Equalize loads",
            "increase_weight": "Increase load",
            "reduce_weight": "Reduce affected set",
            "maintain": "Keep load",
            "deload": "Deload",
            "insufficient_data": "More data needed",
        }[item.action]
        if item.reason_code == "resume_after_deload":
            label = "Return after deload"
        if item.reason_code == "reuse_exercise_baseline":
            label = "Starting loads"
        if item.reason_code in MANUAL_START_REASONS:
            label = "Choose starting load"
        if item.reason_code == "manual_start_selected":
            label = "Starting loads selected"
        if item.reason_code in (
            "deload_load_not_supported",
            "deload_timed_not_supported",
            "bodyweight_load_manual",
            "mixed_load_convention",
        ):
            label = "Manual target"
        original = (
            f"<small>Instead of {escape(self._name(item.planned_exercise_id))}</small>"
            if item.actual_exercise_id != item.planned_exercise_id
            else ""
        )
        sources = []
        for index, (sid, day) in enumerate(zip(item.evidence_session_ids, item.evidence_dates)):
            workout = item.evidence_workouts[index] if index < len(item.evidence_workouts) else ""
            sources.append(
                f"{day:%d %b %Y}" + (f" · {workout}" if workout else "") + f" · session #{sid}"
            )
        evidence = (
            f'<p class="recommendation-source">Based on: {escape("; ".join(sources))}</p>'
            if sources
            else ""
        )
        notices = "".join(f"<p>{escape(notice)}</p>" for notice in item.notices)
        goal = goal_summary(item)
        if not item.goals and planned is not None and item.reason_code in MANUAL_START_REASONS:
            goal = prescription_summary(planned) + " · choose working loads"
        return (
            '<div class="recommendation-exercise"><div class="recommendation-exercise-top">'
            f"<div><strong>{escape(self._name(item.actual_exercise_id))}</strong>{original}</div>"
            f'<span class="recommendation-action recommendation-action--{item.action}">{label}</span></div>'
            f'<div class="recommendation-goal">{escape(goal)}</div>'
            f"<p>{escape(recommendation_note(item))}</p>{notices}{evidence}{reference_html(references)}</div>"
        )
