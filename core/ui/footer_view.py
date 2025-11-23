import streamlit as st

from ..styles.theme_manager import ThemeManager


class FooterView:
    """Enhanced footer with theme integration"""

    def __init__(self, theme: ThemeManager) -> None:
        self.theme: ThemeManager = theme
        self.text: str = (
            "This project was created to visualize my personal gym progress "
            "using Streamlit, MS SQL, and Plotly. "
            "All data is real and comes from my own training records."
        )

    def render(self) -> None:
        """Render enhanced footer"""
        footer_html: str = self.theme.create_footer(self.text)
        st.markdown(footer_html, unsafe_allow_html=True)
