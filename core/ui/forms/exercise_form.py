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
    "Legs",
    "Core",
]


class ExerciseFormView(BaseFormView):
    """Form view for adding a new exercise to the database."""

    def __init__(self) -> None:
        """Initialize the exercise form view."""
        super().__init__("Add New Exercise")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the exercise form with name, category and body part selection."""
        with st.form("exercise_form"):
            name: str = st.text_input("Exercise Name")
            category: str = st.selectbox("Category", EXERCISE_CATEGORIES)
            body_part: str = st.selectbox("Body Part", BODY_PARTS)

            submitted: bool = st.form_submit_button("Add Exercise")

            if submitted:
                if not name or not body_part:
                    st.error("Exercise name and body part are required!")
                    return

                success: bool = self.data_manager.add_exercise(name, category, body_part)

                if success:
                    st.success(f"✅ Exercise '{name}' added successfully!")
                else:
                    st.error("❌ Error while adding exercise.")
