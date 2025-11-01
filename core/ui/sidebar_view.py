import streamlit as st
from ..config import AppConfig

class SidebarView:
    """Enhanced sidebar with better navigation"""
    
    def __init__(self):
        self.config = AppConfig()
        self.sections = self.config.SIDEBAR_SECTIONS
    
    def render(self) -> str:
        """Render sidebar navigation"""
        with st.sidebar:
            # Logo/Title area
            st.markdown(
                """
                <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
                    <h2 style="margin: 0; color: #00ADB5;">💪 GYM DASH</h2>
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.7;">Progress Tracker</p>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Navigation
            st.markdown('<div class="sidebar-title">Nawigacja:</div>', unsafe_allow_html=True)
            
            selected = st.radio(
                label="Wybierz sekcję",
                options=self.sections,
                index=self.sections.index(st.session_state.get('current_section', 'Dashboard')),
                label_visibility="collapsed",
                key="navigation_radio"
            )
            
            # Update session state
            if selected != st.session_state.get('current_section'):
                st.session_state.current_section = selected
                st.rerun()
            
            st.markdown("<br>" * 2, unsafe_allow_html=True)
            
            return selected