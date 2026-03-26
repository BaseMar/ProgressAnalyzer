"""
Sidebar view.

Responsible for:
- global filters (time range)
- navigation between views
"""

from typing import Optional
import pandas as pd
import streamlit as st
from ui.sidebar_upload import SidebarUpload


class SidebarView:
    """
    Sidebar controller for the application UI.

    Responsibilities:
    - render global filters
    - render navigation
    - return user selections
    """

    def render_filters(self, sets_df: pd.DataFrame) -> Optional[str]:
        """
        Render global sidebar filters.

        Currently supported:
        - month selector (YYYY-MM)

        Parameters
        ----------
        sets_df : pd.DataFrame
            Set-level dataframe containing `session_date`.

        Returns
        -------
        Optional[str]
            Selected month in YYYY-MM format, or None.
        """
        st.sidebar.header("Filters")

        if sets_df is None or sets_df.empty:
            st.sidebar.info("No data available.")
            return None

        df = sets_df.copy()
        df["session_date"] = pd.to_datetime(df["session_date"])

        available_months = (df["session_date"].dt.to_period("M").astype(str).sort_values().unique())
        month_options = ["All time", *available_months]
        
        if len(available_months) == 0:
            return None
        
        selected_month = st.sidebar.selectbox("Select month",options=month_options,index=0)
        
        return selected_month

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

        options = [
            "Main Dashboard",
            "Exercises",
            "Body Parts",
            "Analytics",
            "Body Metrics",
        ]

        icons = {
            "Main Dashboard": ":material/dashboard:",
            "Exercises":      ":material/fitness_center:",
            "Body Parts":     ":material/accessibility_new:",
            "Analytics":      ":material/bar_chart:",
            "Body Metrics":   ":material/monitor_weight:",
        }

        # initialise state if missing
        if "nav_selected" not in st.session_state:
            st.session_state.nav_selected = options[0]

        # render buttons vertically inside sidebar
        for opt in options:
            if st.sidebar.button(opt, key=f"nav_{opt}", icon=icons[opt]):
                st.session_state.nav_selected = opt

        return st.session_state.nav_selected

    def render_upload(self) -> None:
        """
        Render workout upload section.
        """
        st.sidebar.divider()
        
        SidebarUpload().render()
        