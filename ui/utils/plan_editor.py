"""Convert editable table values into validated, immutable plan snapshots."""

from datetime import date

import pandas as pd

from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
COLUMNS = ("Order", "Exercise", "Sets", "From", "To", "Unit", "RIR", "Increment")


def capture_plan_drafts():
    """Capture visible inputs before navigation removes their widget state."""
    import streamlit as st
    if "plan_create_new" in st.session_state:
        st.session_state["plan_create_mode"] = st.session_state["plan_create_new"]
    for key in list(st.session_state):
        if key.startswith("plan_editor_") and key.endswith("_draft"):
            capture_draft(key.removesuffix("_draft"), st.session_state[key])


def capture_draft(scope, store):
    import streamlit as st
    if f"{scope}_active_day" in st.session_state:
        store["selected_day"] = st.session_state[f"{scope}_active_day"]
    for field in ("name", "start", "progression_enabled", "block_start", "block_weeks"):
        if f"{scope}_{field}" in st.session_state:
            store[field] = st.session_state[f"{scope}_{field}"]
    for day in store["days"]:
        prefix = f'{scope}_day_{day["uid"]}'
        if f"{prefix}_active_exercise" in st.session_state:
            day["selected_exercise"] = st.session_state[f"{prefix}_active_exercise"]
        for field in ("name", "weekday"):
            if f"{prefix}_{field}" in st.session_state:
                day[field] = st.session_state[f"{prefix}_{field}"]
        for exercise in day["exercises"]:
            for field in ("exercise_id", "sets", "minimum", "maximum", "unit", "rir", "increment"):
                key = f'{prefix}_ex_{exercise["uid"]}_{field}'
                if key in st.session_state:
                    exercise[field] = st.session_state[key]


def exercise_rows(day: TrainingDay | None, labels: dict[int, str]) -> pd.DataFrame:
    rows = []
    if day:
        for order, item in enumerate(day.exercises, start=1):
            rows.append(dict(zip(COLUMNS, (
                order, labels.get(item.exercise_id), item.set_count,
                item.target_min, item.target_max, item.target_unit,
                item.target_rir, item.weight_increment,
            ))))
    else:
        rows.append(dict(zip(COLUMNS, (1, None, 3, 6, 10, "reps", None, None))))
    frame = pd.DataFrame(rows, columns=COLUMNS)
    # Nullable numeric columns must remain editable even when entirely empty.
    for column in ("Order", "Sets", "From", "To", "RIR", "Increment"):
        frame[column] = pd.to_numeric(frame[column]).astype("float64")
    return frame


def _integer(value, label: str) -> int:
    if pd.isna(value) or isinstance(value, bool) or float(value) != int(value):
        raise ValueError(f"{label} must be a whole number")
    return int(value)


def draft_from_editor(name: str, effective_from: date, workouts: list[tuple], catalog: dict[str, int]) -> TrainingPlanDraft:
    days = []
    for day_name, weekday, frame in workouts:
        if frame.empty:
            raise ValueError(f"{day_name or 'Workout'}: add at least one exercise")
        items = []
        orders = set()
        for _, row in frame.iterrows():
            label = row["Exercise"]
            if pd.isna(label) or label not in catalog:
                raise ValueError(f"{day_name or 'Workout'}: choose an exercise from the catalog")
            order = _integer(row["Order"], "Exercise order")
            if order < 1 or order in orders:
                raise ValueError("Exercise order must be positive and unique within each workout")
            orders.add(order)
            items.append((order, PlannedExercise(
                exercise_id=catalog[label], set_count=_integer(row["Sets"], "Sets"),
                target_min=_integer(row["From"], "Range minimum"),
                target_max=_integer(row["To"], "Range maximum"), target_unit=row["Unit"],
                target_rir=None if pd.isna(row["RIR"]) else _integer(row["RIR"], "RIR"),
                weight_increment=None if pd.isna(row["Increment"]) else float(row["Increment"]),
            )))
        days.append(TrainingDay(day_name.strip(), weekday, tuple(item for _, item in sorted(items))))
    return TrainingPlanDraft(name.strip(), effective_from, tuple(days))
