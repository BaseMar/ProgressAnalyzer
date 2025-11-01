import streamlit as st
from ..services.history_service import HistoryService
from ..styles.theme_manager import ThemeManager

class HistoryView:
    """Enhanced history view with better navigation"""
    
    def __init__(self, df_sets, theme: ThemeManager):
        self.service = HistoryService(df_sets)
        self.theme = theme
    
    def render(self):
        """Render full history view"""
        st.header("📅 Historia treningów")
        
        weeks = self.service.get_weeks()
        if not weeks:
            st.info("Brak danych o treningach.")
            return
        
        self._render_week_navigation(weeks)
        self._render_week_details(weeks)
    
    def render_recent(self, limit: int = 5):
        """Render recent training sessions"""
        st.subheader("🕒 Ostatnie treningi")
        
        weeks = self.service.get_weeks()
        if not weeks:
            st.info("Brak danych o treningach.")
            return
        
        # Show recent sessions
        recent_sessions = []
        for year, week in reversed(weeks[-3:]):  # Last 3 weeks
            week_sessions = self.service.get_week_sessions(year, week)
            recent_sessions.extend(week_sessions)
        
        recent_sessions = sorted(recent_sessions, key=lambda x: x['date'], reverse=True)[:limit]
        
        for session in recent_sessions:
            with st.expander(f"📅 {session['date'].strftime('%Y-%m-%d')} - {session['total_sets']} serii"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Liczba serii", session['total_sets'])
                with col2:
                    st.metric("Objętość", f"{session['total_volume']:.0f} kg")
                
                st.markdown("**Ćwiczenia:**")
                for _, ex in session["exercises"].iterrows():
                    st.markdown(f"• **{ex['ExerciseName']}** — {ex['sets']} serii, {ex['total_reps']} powtórzeń")
    
    def _render_week_navigation(self, weeks):
        """Render week navigation controls"""
        current_idx = st.session_state.get("current_week_idx", len(weeks) - 1)
        
        col_prev, col_info, col_next = st.columns([1, 3, 1])
        
        with col_prev:
            if st.button("⬅️ Poprzedni", use_container_width=True) and current_idx > 0:
                st.session_state.current_week_idx = current_idx - 1
                st.rerun()
        
        with col_info:
            year, week = weeks[current_idx]
            st.markdown(f"<h3 style='text-align: center;'>📅 Tydzień {week} / {year}</h3>", unsafe_allow_html=True)
        
        with col_next:
            if st.button("➡️ Następny", use_container_width=True) and current_idx < len(weeks) - 1:
                st.session_state.current_week_idx = current_idx + 1
                st.rerun()
    
    def _render_week_details(self, weeks):
        """Render detailed week information"""
        current_idx = st.session_state.get("current_week_idx", len(weeks) - 1)
        year, week = weeks[current_idx]
        
        week_sessions = self.service.get_week_sessions(year, week)
        
        if not week_sessions:
            st.warning("Brak treningów w tym tygodniu.")
            return
        
        for i, session in enumerate(week_sessions):
            st.markdown(f"#### 🏋️ Sesja {i+1} - {session['date'].strftime('%Y-%m-%d')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Liczba serii", session['total_sets'])
            with col2:
                st.metric("Objętość", f"{session['total_volume']:.0f} kg")
            
            with st.expander("Pokaż szczegóły ćwiczeń"):
                for _, ex in session["exercises"].iterrows():
                    st.markdown(
                        f"• **{ex['ExerciseName']}** — {ex['sets']} serii, "
                        f"{ex['total_reps']} powtórzeń, objętość: {ex['total_volume']:.0f} kg"
                    )