"""
Sidebar view.

Responsible for:
- shortcuts into History
- navigation between views
"""

import streamlit as st


class SidebarView:
    """
    Sidebar controller for the application UI.

    Responsibilities:
    - expose four task-oriented pages
    - render navigation
    - return user selections
    """

    def render_navigation(self) -> str:
        """
        Render navigation section.

        Instead of a radio button list we display a row of tile-like
        buttons. The currently selected section is stored in
        :obj:`st.session_state['nav_selected']` so that the selection
        persists across reruns.

        Returns
        -------
        str
            Selected section name.
        """
        st.sidebar.divider()
        st.sidebar.title("Navigation")

        options = ["Overview", "Analysis", "Plan", "History"]

        icons = {
            "Overview": ":material/dashboard:",
            "Analysis": ":material/bar_chart:",
            "Plan": ":material/calendar_month:",
            "History": ":material/history:",
        }

        aliases = {"Main Dashboard": "Overview", "Training Plan": "Plan", "Exercises": "Analysis",
                   "Body Parts": "Analysis", "Analytics": "Analysis", "Body Metrics": "Analysis"}
        previous = st.session_state.get("nav_selected", "Overview")
        st.session_state.nav_selected = aliases.get(previous, previous) if aliases.get(previous, previous) in options else "Overview"

        for opt in options:
            button_type = "primary" if st.session_state.nav_selected == opt else "secondary"
            st.sidebar.button(
                opt,
                key=f"nav_{opt}",
                icon=icons[opt],
                type=button_type,
                on_click=_set_selected_nav,
                args=(opt,),
            )

        st.sidebar.button("Add workout", key="nav_add_workout", icon=":material/add:", on_click=_open_workout_import)
        return st.session_state.nav_selected



def _set_selected_nav(option: str) -> None:
    from ui.utils.plan_editor import capture_plan_drafts
    capture_plan_drafts()
    st.session_state.nav_selected = option


def _open_workout_import():
    _set_selected_nav("History")
    st.session_state["history_add_workout"] = True
