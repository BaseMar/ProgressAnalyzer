import streamlit as st
from ..styles.theme_manager import ThemeManager

class FooterView:
    """Enhanced footer with theme integration"""
    
    def __init__(self, theme: ThemeManager):
        self.theme = theme
        self.text = (
            "Ten projekt został stworzony, aby wizualizować mój osobisty progres na siłowni "
            "przy użyciu Streamlit, MS SQL oraz Plotly. "
            "Wszystkie dane są prawdziwe i pochodzą z moich własnych zapisów treningowych."
        )
    
    def render(self):
        """Render enhanced footer"""
        footer_html = self.theme.create_footer(self.text)
        st.markdown(footer_html, unsafe_allow_html=True)