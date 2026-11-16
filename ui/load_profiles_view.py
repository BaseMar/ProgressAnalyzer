"""Occasional exercise convention corrections, outside everyday workout capture."""

from dataclasses import replace

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.utils.set_load_inputs import LOAD_LABELS

MODE_LABELS = {
    "external": "External weight",
    "additional": "Additional weight",
    "body_mass": "Body mass only",
    "total": "Body mass + additional weight",
    "assistance": "Assistance",
    "unknown": "Keep unresolved",
}
MODES = {
    "external": ["external"],
    "bodyweight": ["additional", "body_mass", "total"],
    "assisted_bodyweight": ["assistance", "additional", "total"],
}


def render_load_profile_settings(manager):
    with st.expander("Exercise load settings"):
        if not st.toggle("Edit exercise conventions", key="edit_exercise_conventions"):
            return
        try:
            if not manager.exercise_load_profile_storage_ready():
                st.info("Exercise load settings need database migration 011.")
                return
            catalog = manager.load_exercises()
            names = dict(zip(catalog.exercise_id, catalog.exercise_name))
            profiles = manager.load_exercise_load_profiles()
            if not profiles:
                st.info("No exercises yet.")
                return
            eid = st.selectbox(
                "Exercise",
                list(profiles),
                format_func=lambda value: f"{names[value]} · #{value}",
                key="load_profile_exercise",
            )
            profile = profiles[eid]
            kind = st.selectbox(
                "Exercise type",
                list(MODES),
                index=list(MODES).index(profile.load_type),
                format_func=LOAD_LABELS.get,
                key=f"profile_{eid}_kind",
            )
            modes = MODES[kind]
            input_mode = st.selectbox(
                "Kilograms in TXT notes",
                modes,
                index=modes.index(profile.input_mode) if profile.input_mode in modes else 0,
                format_func=MODE_LABELS.get,
                key=f"profile_{eid}_{kind}_input",
            )
            legacy_modes = ["unknown", *modes]
            legacy = st.selectbox(
                "Kilograms in unspecified history",
                legacy_modes,
                index=legacy_modes.index(profile.legacy_mode)
                if profile.legacy_mode in legacy_modes
                else 0,
                format_func=MODE_LABELS.get,
                key=f"profile_{eid}_{kind}_history",
            )
            if st.button("Save exercise convention", key="save_exercise_convention"):
                result = manager.normalize_load_history(
                    exercise_ids=(eid,),
                    overrides=(
                        replace(
                            profile,
                            load_type=kind,
                            input_mode=input_mode,
                            legacy_mode=legacy,
                            source="user",
                        ),
                    ),
                )
                st.success(
                    f"Saved. Normalized {result['converted']} sets; {result['unresolved']} remain unresolved."
                )
                st.rerun()
            report = manager.audit_load_history()
            unresolved = [row for row in report["exercises"] if row["unresolved"]]
            if unresolved:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"Exercise": row["exercise"], "Unresolved sets": row["unresolved"]}
                            for row in unresolved
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
        except (ValueError, TypeError) as error:
            st.error(str(error))
        except SQLAlchemyError:
            st.error("Exercise load settings could not be loaded or saved.")
