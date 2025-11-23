import streamlit as st
from typing import List

from core.data_manager import DataManager

from .base_form import BaseFormView


EXERCISE_CATEGORIES: List[str] = [
    "Push",
    "Pull",
    "Legs",
    "Core",
    "Cardio",
    "Mobility",
    "Accessory",
    "Rehab/Prehab",
]

BODY_PARTS: List[str] = [
    "Chest",
    "Back",
    "Shoulders",
    "Biceps",
    "Triceps",
    "Forearms",
    "Quadriceps",
    "Hamstrings",
    "Glutes",
    "Calves",
    "Abs",
    "Obliques",
    "Full Body",
    "Cardio/Conditioning",
    "Mobility",
]


class ExerciseFormView(BaseFormView):
    """Form view for adding a new exercise to the database."""

    def __init__(self) -> None:
        """Initialize the exercise form view."""
        super().__init__("Dodaj nowe ćwiczenie")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the exercise form with name, category and body part selection."""
        with st.form("exercise_form"):
            name: str = st.text_input("Nazwa ćwiczenia")
            category: str = st.selectbox("Kategoria", EXERCISE_CATEGORIES)
            body_part: str = st.selectbox("Partia mięśniowa", BODY_PARTS)

            submitted: bool = st.form_submit_button("Dodaj ćwiczenie")

            if submitted:
                if not name or not body_part:
                    st.error("Nazwa i partia mięśniowa są wymagane!")
                    return

                success: bool = self.data_manager.add_exercise(name, category, body_part)

                if success:
                    st.success(f"✅ Ćwiczenie '{name}' dodane pomyślnie!")
                else:
                    st.error("❌ Wystąpił błąd przy dodawaniu ćwiczenia.")
