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
)
from ui.utils.copy_workout import copy_workout
from ui.utils.recommendation_sets import recommendation_sets_html
from ui.utils.ui_helpers import section_header

logger = logging.getLogger(__name__)


def recommendation_note(item):
    if item.reason_code == "manual_start_selected":
        return (
            "Saved starting loads. Log and link the workout."
            if item.reason.startswith("Saved starting loads.")
            else "Starting loads for this preview. Log and link the workout."
        )
    notes = {
        "one_more_rep": "Add one rep; keep each set's load and RIR.",
        "upper_range_confirmed": "Every set reached the upper rep limit.",
        "equalize_loads": "Bring lighter sets toward the first working load.",
        "minimum_not_met": "Below the minimum: reduce the affected set by one step.",
        "reduction_step_not_supported": "Choose a lower load manually for the affected set.",
        "manual_start": "Plan context changed. Choose starting loads.",
        "more_time": "Add up to five seconds within the planned range.",
        "time_ceiling_manual": "Time limit reached. Choose a new range or load.",
        "confirm_upper_range": "Repeat the upper rep limit at the planned RIR.",
        "rir_below_target": "Repeat the result; prioritize the planned RIR.",
        "below_range": "Keep the load and work toward the planned range.",
        "mixed_loads": "Keep per-set loads; increases require equal working loads.",
        "mixed_range": "Keep the load until every set reaches the upper limit.",
        "timed_exercise": "Keep the recorded load and planned time range.",
        "bodyweight_load_manual": "Choose added weight or assistance; keep the displayed rep target.",
        "unknown_load": "Complete body mass or assistance in History.",
        "mixed_load_convention": "Load conventions differ. Choose the next load manually.",
        "zero_load": "Keep this target; choose any added load manually.",
        "weight_step_not_supported": "The weight step is too large. Choose the load manually.",
        "scheduled_deload": "Keep repetitions; use lighter loads and RIR 3–4.",
        "resume_after_deload": "Repeat your last regular loads and reps.",
        "no_history": "No usable history. Choose starting loads.",
        "no_normal_baseline": "No regular baseline in this block. Choose starting loads.",
        "reuse_exercise_baseline": "Repeat recorded results at the planned RIR.",
        "changed_set_count": "Keep recorded sets; establish targets for new sets.",
        "prescription_changed": "Keep compatible results at the current plan targets.",
        "incomplete_sets": "Keep known results; complete missing sets in History.",
        "light_sets": "Log regular working sets before increasing the load.",
        "low_effort_sets": "Sets above RIR 5 cannot confirm progression.",
        "missing_rir": "Repeat known results; complete RIR before increasing.",
        "missing_target_rir": "Set target RIR in Plan → Progression & RIR.",
        "history_gap": "Older result: verify it before increasing.",
        "invalid_values": "Correct the recorded load or RIR in History.",
        "deload_load_not_supported": "Choose a lighter deload load manually.",
        "deload_timed_not_supported": "Choose a lighter timed deload target manually.",
        "already_recorded": "Already linked. Select another workout.",
    }
    if item.reason_code in ("missing_weight_step", "invalid_weight_step"):
        if item.actual_exercise_id != item.planned_exercise_id:
            return "Set a positive weight step for this alternative."
        return "Set the available weight step in Plan → Progression & RIR."
    return notes.get(item.reason_code, item.reason)


def recommendation_notices(item):
    """Keep actionable caveats compact; source metadata belongs in History."""
    replacements = {
        "Set purpose inferred from RIR and order; explicit corrections in History take precedence.": None,
        "Additional load is 0 kg; future body mass is not assumed.": None,
        "Legacy kilograms were confirmed as body mass only: additional load is 0 kg.": None,
        "Later heavier trials are capped at the first recorded working load for this start.": "Later heavier sets capped at the first working load.",
        "This starting load comes from older history. Verify it during training before progressing.": "Older history: verify the starting load during training.",
        "Source RIR is incomplete. These recorded loads do not confirm an automatic increase.": "Source RIR is incomplete; verify the starting load.",
        "Possible plateau: four comparable executions without output or confirmed reserve improvement. Review rest, technique and recovery; sets are not added automatically.": "Possible plateau: review rest, technique and recovery.",
    }
    notices = []
    for notice in item.notices:
        if notice.startswith("Source entry #"):
            continue
        if notice.startswith("History contains "):
            notice = notice.split(". ", 1)[0] + "."
        else:
            notice = replacements.get(notice, notice)
        if notice:
            notices.append(notice)
    return tuple(dict.fromkeys(notices))


class NextWorkoutView:
    def __init__(self, manager, exercise_names=None):
        self.dm = manager
        self.names = exercise_names or {}

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self, plan_id, versions, *, context=None, history=None, as_of=None):
        with st.container(key="next_workout_workspace"):
            as_of = as_of or date.today()
            section_header("Next workout", first=True)
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
                    if item.reason_code in MANUAL_START_REASONS and not item.goals
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
                )

            template = workout_template(upcoming, result, self.names)
            with copy_area:
                copy_workout(
                    template, key=f"copy_workout_{plan_id}_{slot.day_id}_{slot.scheduled_date}"
                )
                with st.expander("Copy preview"):
                    st.caption("Paste into Samsung Notes; fill in results and RIR after training.")
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
                "Preview a previously approved alternative. Confirm the actual replacement in History."
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

    def _exercise(self, item, planned=None):
        label = {
            "increase_reps": "Add a rep",
            "increase_time": "Add time",
            "equalize_weight": "Equalize loads",
            "increase_weight": "Increase load",
            "reduce_weight": "Reduce affected set",
            "maintain": "Repeat result",
            "deload": "Deload",
            "insufficient_data": "More data needed",
        }[item.action]
        if item.reason_code == "resume_after_deload":
            label = "Return after deload"
        if item.reason_code == "reuse_exercise_baseline":
            label = "Repeat result"
        if item.reason_code in ("prescription_changed", "changed_set_count") and any(
            g.minimum != g.maximum or g.weight is None for g in item.goals
        ):
            label = "Set target"
        if item.reason_code in MANUAL_START_REASONS and not item.goals:
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
        notice_text = " ".join(recommendation_notices(item))
        notices = f"<p>{escape(notice_text)}</p>" if notice_text else ""
        goals = recommendation_sets_html(item)
        if not item.goals:
            fallback = (
                prescription_summary(planned) + " · choose working loads"
                if planned is not None and item.reason_code in MANUAL_START_REASONS
                else goal_summary(item)
            )
            goals = f'<div class="recommendation-goal">{escape(fallback)}</div>'
        return (
            '<div class="recommendation-exercise"><div class="recommendation-exercise-top">'
            f"<div><strong>{escape(self._name(item.actual_exercise_id))}</strong>{original}</div>"
            f'<span class="recommendation-action recommendation-action--{item.action}">{label}</span></div>'
            f"{goals}"
            f"<p>{escape(recommendation_note(item))}</p>{notices}</div>"
        )
