import streamlit as st
from core.data_manager import DataManager
from .base_form import BaseFormView
from datetime import date

class SessionFormView(BaseFormView):
    """Formularz dodawania nowej sesji treningowej."""

    def __init__(self):
        super().__init__("Dodaj sesję treningową")
        self.data_manager = DataManager()

    def render_form(self):
        with st.form("session_form"):
            session_date = st.date_input("Data sesji", date.today())
            notes = st.text_area("Notatki (opcjonalnie)")

            submitted = st.form_submit_button("Dodaj sesję")

            if submitted:
                success = self.data_manager.add_session(session_date, notes)
                
                if success:
                    st.success(f"✅ Sesja z dnia {session_date} została dodana!")
                else:
                    st.error("❌ Błąd podczas dodawania sesji treningowej.")
