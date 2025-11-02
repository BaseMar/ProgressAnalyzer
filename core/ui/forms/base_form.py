import streamlit as st
from abc import ABC, abstractmethod

class BaseFormView(ABC):
    """Bazowa klasa dla formularzy do wprowadzania danych."""

    def __init__(self, title: str):
        self.title = title

    def render_header(self):
        st.markdown(f"{self.title}")

    @abstractmethod
    def render_form(self):
        """Każdy formularz implementuje tę metodę."""
        pass

    def render(self):
        """Metoda wywoływana z głównego widoku."""
        self.render_header()
        self.render_form()
