import streamlit as st
from core.data_manager import DataManager
from .base_form import BaseFormView
from datetime import date

class SessionFormView(BaseFormView):
    """Formularz dodawania nowej sesji treningowej."""

    def __init__(self):
        super().__init__("### 🏋️ Dodaj nową sesję treningową")
        self.data_manager = DataManager()

    def render_form(self):
        # --- Wczytanie listy ćwiczeń z bazy ---
        exercises_df = self.data_manager.load_exercises()
        exercise_names = exercises_df["ExerciseName"].tolist()

        # --- Dane do sesji ---
        session_date = st.date_input("Data sesji", date.today(), key="session_date")
        notes = st.text_area("Notatki (opcjonalnie)", key="session_notes")
        
        st.markdown("---")
        st.subheader("Wykonane ćwiczenia")

        selected_exercise = st.selectbox("Wybierz ćwiczenie", exercise_names)

        # --- Liczba serii ---
        num_sets = st.number_input("Liczba serii", min_value=1, max_value=10, value=st.session_state.get("num_sets", 3), key="num_sets",)

        # --- Dynamiczne pola dla każdej serii ---
        st.markdown("#### Seria i obciążenie")
        sets_data = []
        for i in range(num_sets):
            st.markdown(f"**Seria {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                reps = st.number_input(
                    f"Powtórzenia (Seria {i+1})",
                    min_value=1,
                    value=10,
                    key=f"reps_{i}",
                )
            with col2:
                weight = st.number_input(
                    f"Ciężar [kg] (Seria {i+1})",
                    min_value=0.0,
                    value=20.0,
                    step=0.5,
                    key=f"weight_{i}",
                )
            sets_data.append({"reps": reps, "weight": weight})
        
        # --- Formularz--- 
        with st.form("confirm_form"):
            submitted = st.form_submit_button("💾 Zapisz sesję")

            if submitted:
                success = self.data_manager.add_full_session(session_date, notes, selected_exercise, sets_data)
                if success:
                    st.success(f"✅ Sesja z dnia {session_date} została dodana pomyślnie!")
                else:
                    st.error("❌ Błąd podczas dodawania sesji.")
