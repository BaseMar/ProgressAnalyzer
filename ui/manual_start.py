"""Manual working-load preview with the original recorded results in view."""

from dataclasses import replace
from html import escape

import streamlit as st

from db.starting_loads import MANUAL_START_REASONS, starting_load_key
from metrics.load_metrics import suggested_load_type
from models.progression import SetGoal


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
        context = record["workout"] or "not linked to a plan"
        sets = []
        for item in record["sets"]:
            quantity = (
                f"{item.duration_seconds}s" if item.duration_seconds else f"{item.repetitions} reps"
            )
            load = f"{item.weight:g} kg recorded"
            if item.load and item.load.load_type in ("bodyweight", "assisted_bodyweight"):
                load = f"bodyweight + {item.weight:g} kg"
                if item.load.assistance_kg is not None:
                    load += f"; assistance {item.load.assistance_kg:g} kg"
            reserve = f"RIR {item.rir}" if item.rir is not None else "RIR unknown"
            purpose = " · warm-up" if item.is_warmup is True else ""
            sets.append(f"S{item.set_number}: {load} × {quantity}, {reserve}{purpose}")
        lines.append(
            f"Last recorded: {record['date']:%d %b %Y} · {context} · session #{record['session_id']}"
            f" · entry #{record['workout_exercise_id']}. " + " / ".join(sets)
        )
    if len(records) > 1:
        lines.append(
            "Several separate entries exist in this session; none is selected automatically."
        )
    return lines


def reference_html(records):
    return "".join(
        f'<p class="recommendation-source">{escape(line)}</p>' for line in reference_texts(records)
    )


def selected_start(item, goals, *, saved):
    return replace(
        item,
        goals=tuple(goals),
        reason_code="manual_start_selected",
        reason=("Saved starting loads. " if saved else "Working loads selected for this preview. ")
        + "Use the planned range and reserve. Log and link the actual workout to establish the new baseline; training history then takes priority.",
    )


def choose_starting_loads(result, upcoming, names, references, manager):
    """Remember complete choices without treating them as logged performances."""
    manual = [item for item in result.exercises if item.reason_code in MANUAL_START_REASONS]
    if not manual or result.block.phase not in ("normal", "unconfigured"):
        return result
    planned = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    storage_ready = manager.starting_load_storage_ready()
    saved_loads = {
        item.plan_exercise_id: manager.load_starting_loads(upcoming, item, result.block)
        if storage_ready
        else ()
        for item in manual
    }
    choices = {
        item.plan_exercise_id: selected_start(item, saved_loads[item.plan_exercise_id], saved=True)
        for item in manual
        if saved_loads[item.plan_exercise_id]
    }
    editing = False
    if len(choices) == len(manual):
        editing = st.toggle(
            "Edit starting loads",
            key=f"edit_starting_loads_{upcoming.slot.day_id}_{upcoming.slot.scheduled_date}",
        )
        if not editing:
            return replace(
                result,
                exercises=tuple(
                    choices.get(item.plan_exercise_id, item) for item in result.exercises
                ),
            )
    with st.expander(
        "Edit starting loads" if editing else "Choose starting loads", expanded=editing
    ):
        st.caption(
            "No usable starting-load history was found for these exercises. Enter any missing loads below; complete choices are saved automatically. Recorded training history takes priority once available."
        )
        if not storage_ready:
            st.warning(
                "Starting loads can be previewed, but saving is unavailable until database setup is updated."
            )
        for item in manual:
            exercise = planned[item.plan_exercise_id]
            saved = saved_loads[item.plan_exercise_id]
            name = names.get(item.actual_exercise_id, f"Exercise #{item.actual_exercise_id}")
            st.markdown(f"**{escape(name)}** · {prescription_summary(exercise)}")
            st.caption(item.reason)
            records = references.get(item.actual_exercise_id, ())
            for line in reference_texts(records):
                st.caption(line)
            if not records:
                st.caption("No earlier record found for this exact exercise.")
            load_type = suggested_load_type(name)
            is_bodyweight = load_type in ("bodyweight", "assisted_bodyweight")
            if is_bodyweight:
                st.caption(
                    "Enter additional load or assistance, not body mass. Historical kilograms are not converted into a future setting."
                )
            context_key = starting_load_key(upcoming, item, result.block)
            scope = f"manual_start_{context_key}_{item.scheduled_date}"
            # Refresh old widgets when another preview or browser tab saves a change.
            saved_values = tuple((goal.weight, goal.assistance_kg) for goal in saved)
            marker = f"{scope}_saved"
            if st.session_state.get(marker) != saved_values or any(
                f"{scope}_load_{index}" not in st.session_state
                for index in range(exercise.set_count)
            ):
                for index in range(exercise.set_count):
                    st.session_state[f"{scope}_load_{index}"] = (
                        saved[index].weight if saved else None
                    )
                    st.session_state[f"{scope}_assistance_{index}"] = (
                        saved[index].assistance_kg if saved else None
                    )
                st.session_state[marker] = saved_values
            goals = []
            for index in range(exercise.set_count):
                weight = st.number_input(
                    f"{name} · set {index + 1} · "
                    + ("additional load (kg)" if is_bodyweight else "load (kg)"),
                    min_value=0.0,
                    value=None,
                    step=float(exercise.weight_increment or 0.5),
                    key=f"{scope}_load_{index}",
                    placeholder="Choose load",
                )
                assistance = None
                if load_type == "assisted_bodyweight":
                    assistance = st.number_input(
                        f"{name} · set {index + 1} · assistance (kg)",
                        min_value=0.0,
                        value=None,
                        step=1.0,
                        key=f"{scope}_assistance_{index}",
                        placeholder="Choose assistance",
                    )
                goals.append(
                    SetGoal(
                        weight,
                        exercise.target_min,
                        exercise.target_max,
                        exercise.target_unit,
                        load_type="assisted_bodyweight"
                        if load_type == "assisted_bodyweight"
                        else "bodyweight"
                        if is_bodyweight
                        else "external",
                        assistance_kg=assistance,
                    )
                )
            complete = all(
                g.weight is not None
                and (g.load_type != "assisted_bodyweight" or g.assistance_kg is not None)
                for g in goals
            )
            if complete:
                if storage_ready:
                    if tuple(goals) != saved:
                        manager.save_starting_loads(upcoming, item, result.block, tuple(goals))
                        st.session_state[marker] = tuple(
                            (goal.weight, goal.assistance_kg) for goal in goals
                        )
                    st.caption(
                        "Starting loads saved. Use Edit starting loads to change them until training history establishes the next target."
                    )
                choices[item.plan_exercise_id] = selected_start(item, goals, saved=storage_ready)
            else:
                choices.pop(item.plan_exercise_id, None)
    if storage_ready and not editing and len(choices) == len(manual):
        # Rebuild immediately after the final save so the setup form disappears.
        st.rerun()
    return replace(
        result,
        exercises=tuple(choices.get(item.plan_exercise_id, item) for item in result.exercises),
    )
