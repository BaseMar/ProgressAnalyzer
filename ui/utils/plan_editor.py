"""Preserve the workout editor draft across page navigation."""

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def capture_plan_drafts():
    """Capture visible inputs before navigation removes their widget state."""
    import streamlit as st

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
        prefix = f"{scope}_day_{day['uid']}"
        if f"{prefix}_active_exercise" in st.session_state:
            day["selected_exercise"] = st.session_state[f"{prefix}_active_exercise"]
        for field in ("name", "weekday"):
            if f"{prefix}_{field}" in st.session_state:
                day[field] = st.session_state[f"{prefix}_{field}"]
        for exercise in day["exercises"]:
            for field in ("exercise_id", "sets", "minimum", "maximum", "unit", "rir", "increment"):
                key = f"{prefix}_ex_{exercise['uid']}_{field}"
                if key in st.session_state:
                    exercise[field] = st.session_state[key]
