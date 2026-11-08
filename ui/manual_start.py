"""Manual working-load preview with the original recorded results in view."""
from dataclasses import replace
from html import escape

import streamlit as st

from metrics.load_metrics import suggested_load_type
from models.progression import SetGoal


MANUAL_START_REASONS = frozenset({"no_history", "no_normal_baseline", "manual_start",
                                   "changed_set_count", "history_gap"})


def prescription_summary(planned):
    unit = "reps" if planned.target_unit == "reps" else "s"
    result = f"{planned.set_count} × {planned.target_min}–{planned.target_max} {unit}"
    if planned.target_rir is not None and planned.target_unit == "reps":
        result += f" · RIR ≥ {planned.target_rir}"
    return result


def reference_texts(records):
    """Raw entries stay separate and are never presented as recommended loads."""
    lines = []
    for record in records:
        context = record['workout'] or 'not linked to a plan'
        sets = []
        for item in record['sets']:
            quantity = f"{item.duration_seconds}s" if item.duration_seconds else f"{item.repetitions} reps"
            load = f"{item.weight:g} kg recorded"
            if item.load and item.load.load_type in ('bodyweight', 'assisted_bodyweight'):
                load = f"bodyweight + {item.weight:g} kg"
                if item.load.assistance_kg is not None:
                    load += f"; assistance {item.load.assistance_kg:g} kg"
            reserve = f"RIR {item.rir}" if item.rir is not None else 'RIR unknown'
            purpose = ' · warm-up' if item.is_warmup is True else ''
            sets.append(f"S{item.set_number}: {load} × {quantity}, {reserve}{purpose}")
        lines.append(f"Last recorded: {record['date']:%d %b %Y} · {context} · session #{record['session_id']}"
                     f" · entry #{record['workout_exercise_id']}. " + ' / '.join(sets))
    if len(records) > 1:
        lines.append('Several separate entries exist in this session; none is selected automatically.')
    return lines


def reference_html(records):
    return ''.join(f'<p class="recommendation-source">{escape(line)}</p>' for line in reference_texts(records))


def choose_starting_loads(result, upcoming, names, references):
    """Session-local choices affect the copyable preview, never stored results."""
    manual = [item for item in result.exercises if item.reason_code in MANUAL_START_REASONS]
    if not manual or result.block.phase not in ('normal', 'unconfigured'):
        return result
    planned = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    choices = {}
    with st.expander('Choose starting loads'):
        st.caption('Enter each working-set load using the history below. These choices apply only to this workout preview and the copied note. After training, log the actual results and link the session to establish a baseline.')
        for item in manual:
            exercise = planned[item.plan_exercise_id]
            name = names.get(item.actual_exercise_id, f'Exercise #{item.actual_exercise_id}')
            st.markdown(f'**{escape(name)}** · {prescription_summary(exercise)}')
            st.caption(item.reason)
            records = references.get(item.actual_exercise_id, ())
            for line in reference_texts(records):
                st.caption(line)
            if not records:
                st.caption('No earlier record found for this exact exercise.')
            load_type = suggested_load_type(name)
            is_bodyweight = load_type in ('bodyweight', 'assisted_bodyweight')
            if is_bodyweight:
                st.caption('Enter additional load or assistance, not body mass. Historical kilograms are not converted into a future setting.')
            scope = f'manual_start_{item.plan_exercise_id}_{item.actual_exercise_id}_{item.scheduled_date}'
            goals = []
            for index in range(exercise.set_count):
                weight = st.number_input(f'{name} · set {index + 1} · ' + ('additional load (kg)' if is_bodyweight else 'load (kg)'),
                    min_value=0., value=None, step=float(exercise.weight_increment or 0.5),
                    key=f'{scope}_load_{index}', placeholder='Choose load')
                assistance = None
                if load_type == 'assisted_bodyweight':
                    assistance = st.number_input(f'{name} · set {index + 1} · assistance (kg)',
                        min_value=0., value=None, step=1., key=f'{scope}_assistance_{index}', placeholder='Choose assistance')
                goals.append(SetGoal(weight, exercise.target_min, exercise.target_max, exercise.target_unit,
                    load_type='assisted_bodyweight' if load_type == 'assisted_bodyweight' else 'bodyweight' if is_bodyweight else 'external',
                    assistance_kg=assistance))
            complete = all(g.weight is not None and (g.load_type != 'assisted_bodyweight' or g.assistance_kg is not None) for g in goals)
            if complete:
                choices[item.plan_exercise_id] = replace(item, goals=tuple(goals), reason_code='manual_start_selected',
                    reason='Working loads selected manually for this preview. Use the planned range and reserve. Log and link the actual workout to establish the new baseline.')
    return replace(result, exercises=tuple(choices.get(item.plan_exercise_id, item) for item in result.exercises))
