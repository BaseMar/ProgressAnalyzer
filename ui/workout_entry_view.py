"""Manual exercise entry alongside the TXT workout importer."""
from datetime import date
from collections import Counter
import logging

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.utils.exercise_matcher import normalize
from ui.utils.set_load_inputs import make_set_load, render_load_inputs, render_total_loads, suggested_load_type

logger = logging.getLogger(__name__)


def render_workout_entry(manager):
    st.subheader("Enter exercise")
    try:
        if not manager.set_load_storage_ready():
            st.info("Manual load entry needs database setup. TXT import remains available.")
            return
        catalog = manager.load_exercises()
        if catalog.empty:
            st.info("Add an exercise to the catalog first.")
            return
        names = dict(zip(catalog.exercise_id, catalog.exercise_name))
        counts = Counter(names.values())
        labels = {key: name + (f" · #{key}" if counts[name] > 1 else "") for key, name in names.items()}
        day = st.date_input("Workout date", value=date.today(), key="entry_date")
        exercise_id = st.selectbox("Exercise", list(names), format_func=labels.get, key="entry_exercise")
        key = f"entry_{exercise_id}"
        default_measure = 1 if "deadhang" in "".join(normalize(names[exercise_id]).split()) else 0
        measure = st.radio("Measure", ["Repetitions", "Seconds"], index=default_measure,
                           horizontal=True, key=f"{key}_measure")
        settings = render_load_inputs(manager, day, key=key,
            default=suggested_load_type(names[exercise_id]), allow_legacy=False)
        count = st.number_input("Number of sets", min_value=1, max_value=50, value=3, step=1, key=f"{key}_count")
        value_column = "Seconds" if measure == "Seconds" else "Reps"
        base = pd.DataFrame({"Set": range(1, count + 1), value_column: [30 if measure == "Seconds" else 8] * count,
            "kg": [0.0] * count, "RIR": pd.Series([None] * count, dtype="float64"), "Purpose": ["Working"] * count})
        edited = st.data_editor(base, key=f"{key}_{measure}_{count}_sets", hide_index=True, width="stretch",
            disabled=["Set"], column_config={
                value_column: st.column_config.NumberColumn(value_column, min_value=1, step=1, required=True),
                "kg": st.column_config.NumberColumn("Weight (kg)" if settings[0] == "external" else "Additional kg", min_value=0., required=True),
                "RIR": st.column_config.NumberColumn("RIR", min_value=0, step=1),
                "Purpose": st.column_config.SelectboxColumn("Purpose", options=["Unknown", "Working", "Warm-up"], required=True),
            })
        st.caption("Save one exercise at a time. Exercises entered for the same date are appended to that day's latest session.")
        render_total_loads(settings, edited["kg"])
        if not st.button("Save exercise", type="primary", key="entry_save"):
            return
        sets = []
        for row in edited.to_dict("records"):
            amount = row[value_column]
            if pd.isna(amount) or float(amount) != int(amount) or amount <= 0:
                raise ValueError("Enter a positive whole number of reps or seconds for every set")
            if row["Purpose"] not in ("Unknown", "Working", "Warm-up"):
                raise ValueError("Choose a purpose for every set")
            rir = row["RIR"]
            if not pd.isna(rir) and (float(rir) != int(rir) or rir < 0):
                raise ValueError("RIR must be a non-negative whole number or empty")
            load = make_set_load(settings, row["kg"])
            sets.append({"reps": 0 if measure == "Seconds" else int(amount),
                "duration_seconds": int(amount) if measure == "Seconds" else None,
                "weight": float(row["kg"]), "rir": None if pd.isna(rir) else int(rir), "load": load,
                "is_warmup": {"Unknown": None, "Working": False, "Warm-up": True}[row["Purpose"]]})
        manager.add_full_session(day, "Manual entry", names[exercise_id], sets, None, None, exercise_id=int(exercise_id))
        st.session_state["history_workout_notice"] = f"Saved {names[exercise_id]} · {len(sets)} sets."
        st.session_state["history_calendar_month"] = f"{day:%Y-%m}"
        st.session_state["history_month"] = f"{day:%Y-%m}"
        st.session_state[f"history_day_{day:%Y-%m}"] = day
        st.session_state["history_add_workout"] = False
        st.rerun()
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
    except SQLAlchemyError:
        logger.exception("Manual workout entry failed")
        st.error("The exercise could not be saved. Your entries are still here.")
