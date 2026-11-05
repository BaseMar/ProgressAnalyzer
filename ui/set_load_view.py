"""Explicit per-set load corrections inside recorded workout history."""
import logging

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from mapper import map_workout_set
from ui.utils.set_load_inputs import format_load, make_set_load, render_load_inputs, render_total_loads

logger = logging.getLogger(__name__)


def render_set_load_correction(manager, *, session_id, workout_date):
    with st.expander("Body mass and load details"):
        if not st.toggle("Edit set load", key=f"edit_load_{session_id}"):
            return
        try:
            if not manager.set_load_storage_ready():
                st.info("Load corrections need database setup.")
                return
            frame = manager.load_session_sets(session_id)
            if frame.empty:
                st.info("No sets to edit.")
                return
            rows = {int(row["set_id"]): row for row in frame.to_dict("records")}
            set_id = st.selectbox("Set to edit", list(rows), key=f"load_set_{session_id}",
                format_func=lambda value: f"{rows[value]['exercise_name']} · set {rows[value]['set_number']}")
            row = rows[set_id]
            current = map_workout_set(row).load
            if current is not None:
                st.caption("Saved: " + format_load(current))
            else:
                st.caption("The original load convention is unspecified. Check whether the recorded kg include body mass before selecting a type.")
            key = f"load_{session_id}_{set_id}"
            settings = render_load_inputs(manager, workout_date, key=key, current=current,
                default=current.load_type if current is not None else "legacy")
            if settings[0] == "legacy":
                st.caption("Original kg values will be preserved.")
                weight = row["weight"]
            else:
                weight = st.number_input("Weight (kg)" if settings[0] == "external" else "Additional weight (kg)",
                    min_value=0., value=float(row["weight"]), step=0.5, key=f"{key}_weight")
            render_total_loads(settings, [weight])
            if st.button("Save set load", key=f"{key}_save"):
                manager.save_session_set_loads(session_id, {set_id: make_set_load(settings, weight)})
                st.cache_data.clear()
                st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
        except SQLAlchemyError:
            logger.exception("Set load correction failed")
            st.error("The load could not be loaded or saved. Please try again.")
