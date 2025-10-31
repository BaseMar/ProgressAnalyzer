import streamlit as st
from core.services.history_service import HistoryService

class HistoryView:
    """
    Klasa odpowiedzialna za wyświetlanie historii treningów w Streamlit.
    """

    def __init__(self, df_sets):
        self.service = HistoryService(df_sets)

    def render(self):
        st.subheader("Historia treningów")

        weeks = self.service.get_weeks()
        if not weeks:
            st.info("Brak danych o treningach.")
            return

        current_idx = st.session_state.get("current_week_idx", len(weeks) - 1)
        col_prev, col_info, col_next = st.columns([1, 3, 1])
        with col_prev:
            if st.button("⬅️ Poprzedni tydzień", use_container_width=True) and current_idx > 0:
                st.session_state.current_week_idx = current_idx - 1
                st.rerun()
        with col_next:
            if st.button("➡️ Następny tydzień", use_container_width=True) and current_idx < len(weeks) - 1:
                st.session_state.current_week_idx = current_idx + 1
                st.rerun()

        year, week = weeks[current_idx]
        st.markdown(f"### Tydzień {week} / {year}")

        week_sessions = self.service.get_week_sessions(year, week)
        if not week_sessions:
            st.warning("Brak treningów w tym tygodniu.")
            return

        for session in week_sessions:
            st.markdown(f"#### {session['date'].strftime('%Y-%m-%d')}")
            st.write(f"**Liczba serii:** {session['total_sets']} | **Objętość:** {session['total_volume']}")
            
            with st.expander("Pokaż ćwiczenia"):
                for _, ex in session["exercises"].iterrows():
                    st.markdown(
                        f"- **{ex['ExerciseName']}** — {ex['sets']} serii, "
                        f"{ex['total_reps']} powtórzeń, "
                        f"objętość: {ex['total_volume']:.0f}"
                    )
