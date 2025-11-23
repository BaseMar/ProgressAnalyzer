from datetime import date

from typing import Any, Dict, List

import streamlit as st

from core.data_manager import DataManager

from .base_form import BaseFormView


class SessionFormView(BaseFormView):
    """Form view for adding a new workout session with exercises and sets."""

    def __init__(self) -> None:
        """Initialize the workout session form view."""
        super().__init__("Dodaj nową sesję treningową")
        self.data_manager: DataManager = DataManager()

    def render_form(self) -> None:
        """Render the workout session form with exercise selection and set input."""
        # --- Load list of exercises from database ---
        exercises_df: Any = self.data_manager.load_exercises()
        exercise_names: List[str] = exercises_df["ExerciseName"].tolist()

        # --- Dane do sesji ---
        session_date: date = st.date_input("Data sesji", date.today(), key="session_date")
        notes: str = st.text_area("Notatki (opcjonalnie)", key="session_notes")

        st.markdown("---")
        st.subheader("Wykonane ćwiczenia")

        selected_exercise: str = st.selectbox("Wybierz ćwiczenie", exercise_names)

        # --- Liczba serii ---
        num_sets: int = st.number_input(
            "Liczba serii",
            min_value=1,
            max_value=10,
            value=st.session_state.get("num_sets", 3),
            key="num_sets",
        )

        # --- Dynamiczne pola dla każdej serii ---
        st.markdown("#### Seria i obciążenie")
        sets_data: List[Dict[str, Any]] = []
        for i in range(num_sets):
            st.markdown(f"**Seria {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                reps: int = st.number_input(
                    f"Powtórzenia (Seria {i+1})",
                    min_value=1,
                    value=10,
                    key=f"reps_{i}",
                )
            with col2:
                weight: float = st.number_input(
                    f"Ciężar [kg] (Seria {i+1})",
                    min_value=0.0,
                    value=20.0,
                    step=0.5,
                    key=f"weight_{i}",
                )
            sets_data.append({"reps": reps, "weight": weight})

        # --- Formularz---
        with st.form("confirm_form"):
            submitted: bool = st.form_submit_button("💾 Zapisz sesję")

            if submitted:
                success: bool = self.data_manager.add_full_session(
                    session_date, notes, selected_exercise, sets_data
                )
                if success:
                    st.success(
                        f"✅ Sesja z dnia {session_date} została dodana pomyślnie!"
                    )
                else:
                    st.error("❌ Błąd podczas dodawania sesji.")
