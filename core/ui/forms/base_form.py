from abc import ABC, abstractmethod
from typing import Any

import streamlit as st


class BaseFormView(ABC):
    """Abstract base class for data entry forms.

    Subclasses must implement the render_form method to define form-specific UI
    and form submission logic.
    """

    def __init__(self, title: str) -> None:
        """Initialize the form with a title string."""
        self.title: str = title

    def render_header(self) -> None:
        """Render the form header using Streamlit markdown."""
        st.markdown(f"{self.title}")

    @abstractmethod
    def render_form(self) -> None:
        """Abstract method that each subclass must implement to render the form UI."""
        raise NotImplementedError()

    def render(self) -> None:
        """Entry point to render the entire form (header + form fields)."""
        self.render_header()
        self.render_form()
