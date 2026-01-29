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
            Set-level dataframe containing `SessionDate`.

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
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])

        available_months = (df["SessionDate"].dt.to_period("M").astype(str).sort_values().unique())

        if len(available_months) == 0:
            return None

        return st.sidebar.selectbox("Select month",options=available_months, index=len(available_months) - 1)

    def render_navigation(self) -> str:
        """
        Render navigation section.

        Returns
        -------
        str
            Selected section name.
        """
        st.sidebar.divider()
        st.sidebar.title("Navigation")

        return st.sidebar.radio("Choose section:", ["Main Dashboard", "Exercises", "Body Parts"])

    def render_upload(self) -> None:
        """
        Render workout upload section.
        """
        st.sidebar.divider()
        
        SidebarUpload().render()
