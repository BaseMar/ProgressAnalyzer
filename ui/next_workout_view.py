"""Compact next-session targets; historical analytics remain separate."""
from datetime import date, timedelta
from html import escape
import logging

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from metrics.plan_performance import comparison_context, compute_plan_performance
from metrics.overview_summary import workout_focus
from metrics.utils.recommendation_text import goal_summary
from models.plan_adherence import PlannedTarget, PlannedWorkout
from models.training_insights import WorkoutPreview
from ui.utils.ui_helpers import section_header

logger = logging.getLogger(__name__)


def approved_alternatives(history, slot, planned_exercises, *, as_of):
    """Only explicitly approved, logged alternatives in the same plan context."""
    rows = compute_plan_performance(history, as_of=as_of)
    return {
        position: sorted({row["actual_exercise_id"] for row in rows
            if row["actual_exercise_id"] != planned.exercise_id and row["sets"]
            and row["performed_on"] is not None and row["performed_on"] <= as_of
            and row["context"] == comparison_context(slot, position, planned, row["actual_exercise_id"])})
        for position, planned in enumerate(planned_exercises, start=1)
    }


def recommendation_note(item):
    notes = {
        "one_more_rep": "Add one total rep while keeping the same load and reserve.",
        "upper_range_confirmed": "Upper range confirmed across consecutive workouts. Add one equipment step.",
        "confirm_upper_range": "Repeat the upper range with enough reserve before increasing weight.",
        "rir_below_target": "Keep the load: at least one previous set had less reserve than planned.",
        "below_range": "Keep the load and work towards the planned repetition range.",
        "mixed_loads": "Keep each set's logged load; automatic increases need one common working load.",
        "mixed_range": "Some sets exceeded the range while others stayed below its upper bound.",
        "timed_exercise": "Keep the logged load and time range; automatic timed progression is not supported.",
        "zero_load": "Keep this target; adding external load requires a manual decision.",
        "weight_step_not_supported": "The available weight step is too large for an automatic increase.",
        "scheduled_deload": "Lighter week: fewer sets, reduced load and more reserve.",
        "resume_after_deload": "Return to the last ordinary loads. Establish progression again in this block.",
        "no_history": "Log and link a comparable workout to establish a baseline.",
        "no_normal_baseline": "Log and link a normal workout for this exercise to establish a baseline.",
        "incomplete_sets": "Review the latest linked workout: its matching working-set count is incomplete.",
        "light_sets": "Light sets remain in history; log the planned ordinary work before increasing the target.",
        "low_effort_sets": "Sets above RIR 5 remain in history and do not establish an ordinary progression target.",
        "missing_rir": "Complete the missing RIR values in the source workout.",
        "missing_target_rir": "Set target RIR in Training Plan → Progression & RIR.",
        "history_gap": "The last comparable workout is too old. Establish a new baseline.",
        "invalid_values": "Review the source workout's load and RIR values.",
        "deload_load_not_supported": "Choose a deload load manually; this load or equipment step is unsupported.",
        "deload_timed_not_supported": "Choose a timed deload target manually; automatic targets are not supported.",
        "already_recorded": "This workout has already been linked. Select another upcoming workout.",
    }
    if item.reason_code in ("missing_weight_step", "invalid_weight_step"):
        if item.actual_exercise_id != item.planned_exercise_id:
            return "Enter a positive weight step for this alternative in the options above."
        return "Set the available weight step in Training Plan → Progression & RIR."
    return notes.get(item.reason_code, item.reason)


class NextWorkoutView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.names = exercise_names or {}

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self, plan_id, versions, *, history=None, as_of=None, compact=False):
        as_of = as_of or date.today()
        section_header("Next workout")
        try:
            return self._render(plan_id, versions, history, as_of, compact=compact)
        except SQLAlchemyError:
            logger.exception("Unable to load next-workout recommendations")
            st.error("Next-workout targets could not be loaded. Your recorded history is still available.")
        except ValueError:
            logger.exception("Next-workout selection is no longer valid")
            st.info("The plan or workout assignment changed. Refresh this view to select the next workout.")

    def _render(self, plan_id, versions, history, as_of, *, compact=False):
        if not versions:
            st.info("Save a Training Plan to see the next workout.")
            return
        first = max(as_of, min(version.draft.effective_from for version in versions))
        slots = self.dm.load_scheduled_workouts(plan_id, as_of, first + timedelta(days=28))
        slots = sorted((slot for slot in slots if slot.session_id is None),
                       key=lambda slot: (slot.scheduled_date, slot.position, slot.day_id))
        if not slots:
            st.info("All workouts in the upcoming four-week window are already linked.")
            return
        choices = {f"{slot.day_id}:{slot.scheduled_date}": slot for slot in slots}
        selection_key = f"next_workout_{plan_id}"
        if st.session_state.get(selection_key) not in choices:
            st.session_state[selection_key] = next(iter(choices))
        with st.container(key="next_workout_card"):
            selected = st.selectbox("Upcoming workout", list(choices), key=selection_key,
                format_func=lambda key: f'{choices[key].scheduled_date:%a, %d %b %Y} · {choices[key].name}')
            slot = choices[selected]
            result = self.dm.load_workout_recommendations(plan_id, slot.day_id, slot.scheduled_date, as_of=as_of)
            version = next(version for version in versions if version.version_id == slot.version_id)
            self._heading(slot, result.block, version.draft.progression)
            st.caption("Today and upcoming dates · independent of the history month filter · linked workouts are excluded.")
            if result.block.phase == "unconfigured":
                st.info("Configure a training block in Training Plan → Edit as a new version → Progression & training block to enable targets.")
                return
            if result.block.phase == "not_started":
                st.info(f"The training block starts on {version.draft.progression.block_start:%d %b %Y}. Select a workout on or after that date.")
                return
            if any(item.reason_code == "already_recorded" for item in result.exercises):
                st.info("This workout was linked while the view was loading. Refresh to select another upcoming workout.")
                return
            planned = self.dm.load_scheduled_workout_targets(slot.day_id)
            if history is None:
                history = self.dm.load_plan_performance(plan_id, as_of, slot.scheduled_date)
            alternatives = approved_alternatives(history, slot, planned.exercises, as_of=as_of)
            substitutions, steps = self._alternatives(plan_id, slot, result.exercises, alternatives)
            if substitutions:
                result = self.dm.load_workout_recommendations(plan_id, slot.day_id, slot.scheduled_date,
                    as_of=as_of, substitutions=substitutions, replacement_weight_steps=steps)
            if compact:
                focus = workout_focus(result)
                st.caption(f"{focus.available} of {focus.total} exercise targets available. Full workout includes every planned exercise.")
                if focus.gaps:
                    st.caption("To complete targets: " + "; ".join(
                        f"{gap.count} exercise(s) — {recommendation_note(gap.example)}" for gap in focus.gaps[:2])
                        + (" Further setup details are in Full workout." if len(focus.gaps) > 2 else ""))
                if focus.visible:
                    st.markdown('<div class="recommendation-list">' + ''.join(self._exercise(item) for item in focus.visible) + '</div>', unsafe_allow_html=True)
                with st.expander(f"Full workout · {focus.total} exercises"):
                    st.markdown('<div class="recommendation-list">' + ''.join(self._exercise(item) for item in result.exercises) + '</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="recommendation-list">' + ''.join(self._exercise(item) for item in result.exercises) + '</div>', unsafe_allow_html=True)
            with st.expander("Why these targets?"):
                st.caption("RIR means repetitions in reserve. Working sets are inferred automatically from RIR and sequence; explicit corrections take priority. Deload and timed work use their own context. Targets are rule-based suggestions.")
                for item in result.exercises:
                    st.markdown(f"**{escape(self._name(item.actual_exercise_id))}**")
                    st.caption(item.reason)
                    if item.evidence_session_ids:
                        evidence = ", ".join(f"{day:%d %b %Y} (session #{sid})" for sid, day in zip(item.evidence_session_ids, item.evidence_dates))
                        st.caption(f"Based on: {evidence}")
                st.caption("Normal training: add one total rep; a weight increase requires two upper-range executions on different days. Default history limit: 21 days; maximum weight step: 10%.")
                st.caption("Deload: retain half the sets rounded up, target the lower rep bound, reduce load by 10–20% in whole equipment steps, and target at least RIR 4 (or original RIR + 2). After deload, resume ordinary loads without an increase.")
            return WorkoutPreview(PlannedWorkout(slot, tuple(
                PlannedTarget(item.plan_exercise_id, exercise)
                for item, exercise in zip(result.exercises, planned.exercises))), result)

    @staticmethod
    def _heading(slot, phase, settings):
        label = {"normal": "Normal training", "deload": "Deload", "unconfigured": "Setup needed", "not_started": "Before block"}[phase.phase]
        st.markdown('<div class="recommendation-heading"><div>'
                    f'<span>{slot.scheduled_date:%A, %d %B}</span><strong>{escape(slot.name)}</strong></div>'
                    f'<span class="recommendation-phase recommendation-phase--{phase.phase}">{label}</span></div>', unsafe_allow_html=True)
        if phase.week is not None:
            st.caption(f"Block {phase.cycle} · Week {phase.week} of {settings.block_weeks} · Deload {phase.deload_start:%d %b}–{phase.cycle_end:%d %b}")

    def _alternatives(self, plan_id, slot, recommendations, alternatives):
        substitutions, steps = {}, {}
        if not any(alternatives.values()):
            return substitutions, steps
        scope = f"recommendation_{plan_id}_{slot.day_id}_{slot.scheduled_date}"
        with st.expander("Use a confirmed alternative"):
            st.caption("Choose an alternative previously approved for this workout context. Choices apply to this preview only; confirm the actual replacement after logging the session.")
            for position, item in enumerate(recommendations, start=1):
                if not alternatives[position]:
                    continue
                original = item.planned_exercise_id
                options = [original, *sorted(alternatives[position], key=self._name)]
                key = f"{scope}_{item.plan_exercise_id}_exercise"
                if st.session_state.get(key) not in options:
                    st.session_state[key] = original
                actual = st.selectbox(f"Exercise for {self._name(original)} · position {position}", options,
                    key=key, format_func=lambda value: self._name(value) + (" (planned)" if value == original else ""))
                if actual != original:
                    substitutions[item.plan_exercise_id] = actual
            for actual in sorted(set(substitutions.values())):
                value = st.number_input(f"Weight step · {self._name(actual)} (kg)", min_value=0.01, value=None,
                    step=0.25, format="%.2f", placeholder="e.g. 5.00", key=f"{scope}_step_{actual}",
                    help="Smallest available load change on this equipment, using the same weight convention as your logs.")
                if value is not None:
                    steps[actual] = value
        return substitutions, steps

    def _exercise(self, item):
        label = {"increase_reps": "Add a rep", "increase_weight": "Increase load", "maintain": "Keep load",
                 "deload": "Deload", "insufficient_data": "More data needed"}[item.action]
        if item.reason_code == "resume_after_deload":
            label = "Return after deload"
        if item.reason_code in ("deload_load_not_supported", "deload_timed_not_supported"):
            label = "Manual target"
        original = f'<small>Instead of {escape(self._name(item.planned_exercise_id))}</small>' if item.actual_exercise_id != item.planned_exercise_id else ""
        return ('<div class="recommendation-exercise"><div class="recommendation-exercise-top">'
                f'<div><strong>{escape(self._name(item.actual_exercise_id))}</strong>{original}</div>'
                f'<span class="recommendation-action recommendation-action--{item.action}">{label}</span></div>'
                f'<div class="recommendation-goal">{escape(goal_summary(item))}</div>'
                f'<p>{escape(recommendation_note(item))}</p></div>')
