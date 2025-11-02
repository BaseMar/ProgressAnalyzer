import streamlit as st
from core.data_manager import DataManager
from sqlalchemy import text
from .base_form import BaseFormView

class ExerciseFormView(BaseFormView):
    """Formularz dodawania nowego ćwiczenia."""

    def __init__(self):
        super().__init__("Dodaj nowe ćwiczenie")
        self.data_manager = DataManager()

    def render_form(self):
        with st.form("exercise_form"):
            name = st.text_input("Nazwa ćwiczenia")
            category = st.text_input("Kategoria (np. Push/Pull/Legs)")
            body_part = st.text_input("Partia mięśniowa (np. Chest/Back/Legs)")

            submitted = st.form_submit_button("Dodaj ćwiczenie")

            if submitted:
                if not name or not body_part:
                    st.error("Nazwa i partia mięśniowa są wymagane!")
                    return

                success = self.data_manager.add_exercise(name, category, body_part)

                if success:
                    st.success(f"✅ Ćwiczenie '{name}' dodane pomyślnie!")
                else:
                    st.error("❌ Wystąpił błąd przy dodawaniu ćwiczenia.")
