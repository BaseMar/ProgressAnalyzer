"""Occasional exercise convention corrections, outside everyday workout capture."""

import logging
from collections import Counter
from dataclasses import replace
from html import escape

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from ui.utils.set_load_inputs import LOAD_LABELS

logger = logging.getLogger(__name__)
DATA_SETTINGS_KEY = "history_data_settings_open"
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


def _close_data_settings():
    st.session_state.pop(DATA_SETTINGS_KEY, None)


def _edit_exercise(exercise_id):
    st.session_state["load_profile_exercise"] = exercise_id
    st.session_state["data_settings_tab"] = "Exercise settings"


@st.dialog(
    "Data settings", width="large", icon=":material/settings:", on_dismiss=_close_data_settings
)
def data_settings_dialog(manager):
    st.caption("Choose how exercise loads are recorded and interpreted across your sessions.")
    if "data_settings_notice" in st.session_state:
        st.success(st.session_state.pop("data_settings_notice"))
    try:
        if not manager.exercise_load_profile_storage_ready():
            st.info("Exercise load settings are not available yet. Complete database setup first.")
            return
        settings, unresolved = st.tabs(
            ["Exercise settings", "Unresolved sets"],
            key="data_settings_tab",
            on_change="rerun",
        )
        if settings.open:
            with settings:
                _render_exercise_settings(manager)
        if unresolved.open:
            with unresolved:
                _render_unresolved_sets(manager)
    except (ValueError, TypeError) as error:
        st.error(str(error))
    except SQLAlchemyError:
        logger.exception("Unable to load or save exercise settings")
        st.error("Data settings could not be loaded or saved. Please try again.")


def _render_exercise_settings(manager):
    profiles = manager.load_exercise_load_profiles()
    if not profiles:
        st.info("No exercises yet.")
        return
    names = {
        row["exercise_id"]: row["exercise_name"] for row in manager.load_exercise_load_catalog()
    }
    duplicates = Counter(names.get(eid, f"Exercise #{eid}") for eid in profiles)
    labels = {
        eid: names.get(eid, f"Exercise #{eid}")
        + (f" · #{eid}" if duplicates[names.get(eid, f"Exercise #{eid}")] > 1 else "")
        for eid in profiles
    }
    options = sorted(profiles, key=lambda eid: (labels[eid].casefold(), eid))
    if st.session_state.get("load_profile_exercise") not in profiles:
        st.session_state["load_profile_exercise"] = options[0]
    eid = st.selectbox(
        "Exercise", options, key="load_profile_exercise", format_func=labels.__getitem__
    )
    profile = profiles[eid]
    st.markdown(
        '<div class="data-settings-summary"><span>Current settings</span>'
        f"<strong>{escape(labels[eid])}</strong>"
        '<div class="data-settings-summary-values">'
        f"<span>{escape(LOAD_LABELS[profile.load_type])}</span>"
        f"<span>TXT: {escape(MODE_LABELS[profile.input_mode])}</span>"
        f"<span>History: {escape(MODE_LABELS[profile.legacy_mode])}</span></div></div>",
        unsafe_allow_html=True,
    )
    kind = st.segmented_control(
        "Exercise type",
        list(MODES),
        default=profile.load_type,
        format_func=LOAD_LABELS.get,
        key=f"profile_{eid}_kind",
        required=True,
        wrap=True,
    )
    modes = MODES[kind]
    with st.container(key="data_settings_fields"):
        notes, history = st.columns(2)
        input_mode = notes.selectbox(
            "Kilograms in TXT notes",
            modes,
            index=modes.index(profile.input_mode) if profile.input_mode in modes else 0,
            format_func=MODE_LABELS.get,
            key=f"profile_{eid}_{kind}_input",
        )
        legacy_modes = ["unknown", *modes]
        legacy = history.selectbox(
            "Kilograms in unspecified history",
            legacy_modes,
            index=legacy_modes.index(profile.legacy_mode)
            if profile.legacy_mode in legacy_modes
            else 0,
            format_func=MODE_LABELS.get,
            key=f"profile_{eid}_{kind}_history",
        )
    st.caption(
        "Changes apply to this exercise across all sessions. "
        "Saving also updates its unspecified historical loads using these rules."
    )
    if st.button(
        "Save changes", key="save_exercise_convention", type="primary", icon=":material/save:"
    ):
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
        st.session_state["data_settings_notice"] = (
            f"Saved settings for {names.get(eid, labels[eid])}. "
            f"Updated {result['converted']} historical sets; {result['unresolved']} remain unresolved."
        )
        st.rerun()


def _render_unresolved_sets(manager):
    report = manager.audit_load_history()
    unresolved = sorted(
        (row for row in report["exercises"] if row["unresolved"]),
        key=lambda row: (-row["unresolved"], row["exercise"].casefold(), row["exercise_id"]),
    )
    if not unresolved:
        st.success("No unresolved sets.")
        return
    total = sum(row["unresolved"] for row in unresolved)
    st.markdown(f"**{len(unresolved)} exercises · {total} unresolved sets**")
    st.caption("Choose an exercise to review how its historical kilograms should be interpreted.")
    duplicates = Counter(row["exercise"] for row in unresolved)
    for row in unresolved:
        eid = row["exercise_id"]
        name = row["exercise"] + (f" · #{eid}" if duplicates[row["exercise"]] > 1 else "")
        with st.container(
            key=f"data_settings_unresolved_{eid}", horizontal=True, vertical_alignment="center"
        ):
            st.markdown(
                '<div class="data-settings-unresolved-heading">'
                f"<strong>{escape(name)}</strong>"
                f"<span>{row['unresolved']} unresolved sets</span></div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Edit",
                key=f"data_settings_edit_{eid}",
                icon=":material/edit:",
                type="tertiary",
                on_click=_edit_exercise,
                args=(eid,),
                help=f"Edit load settings for {name}",
            )
