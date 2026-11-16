"""One persistent plan context shared by the current and historical views."""

from collections.abc import Mapping

import streamlit as st


def select_active_plan(plans):
    by_id = (
        dict(plans)
        if isinstance(plans, Mapping)
        else {item.plan_id: item.draft.name for item in plans}
    )
    if not by_id:
        st.session_state.pop("active_plan_id", None)
        return None
    # Keep the domain selection when Streamlit cleans up an off-page widget.
    widget_key = "adherence_plan"
    if st.session_state.get(widget_key) not in by_id:
        st.session_state[widget_key] = (
            st.session_state.get("active_plan_id")
            if st.session_state.get("active_plan_id") in by_id
            else next(iter(by_id))
        )
    selected = st.selectbox(
        "Active plan",
        list(by_id),
        key=widget_key,
        format_func=by_id.__getitem__,
    )
    st.session_state["active_plan_id"] = selected
    return selected
