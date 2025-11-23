import streamlit as st
from typing import List, Optional

from ..config import AppConfig


class SidebarView:
    """Enhanced sidebar with better navigation"""

    def __init__(self) -> None:
        self.config: AppConfig = AppConfig()
        self.sections: Optional[List[str]] = self.config.SIDEBAR_SECTIONS

    def render(self) -> str:
        """Render sidebar navigation"""
        with st.sidebar:
            st.markdown(
                """
                <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
                    <h2 style="margin: 0; color: #00ADB5;">GYM DASH</h2>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7;">Progress Tracker</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="sidebar-title">Nawigacja:</div>', unsafe_allow_html=True
            )

            if "current_section" not in st.session_state:
                st.session_state.current_section = "Dashboard"

            for section in self.sections or []:
                is_current = st.session_state.current_section == section
                if st.button(
                    section,
                    key=f"nav_{section}",
                    width="stretch",
                    type="primary" if is_current else "secondary",
                ):
                    st.session_state.current_section = section
                    st.rerun()
            st.markdown("<br>" * 2, unsafe_allow_html=True)

            return st.session_state.current_section
