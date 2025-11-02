import streamlit as st
from ...styles.theme_manager import ThemeManager

class KPIView:
    """Enhanced KPI display with better formatting"""
    
    def __init__(self, theme: ThemeManager):
        self.theme = theme
    
    def display(self, kpis: dict):
        """Render KPI cards with enhanced styling"""
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        kpi_configs = [
            {
                "title": "Średnia intensywność",
                "value": f"{kpis['avg_intensity']:.1f} kg",
                "delta": f"Δ {kpis['intensity_change']}%"
            },
            {
                "title": "Łączna objętość tygodniowa", 
                "value": f"{kpis['total_volume']:,.0f}".replace(",", " ") + " kg",
                "delta": f"Δ {kpis['volume_change']}%"
            },
            {
                "title": "Liczba sesji",
                "value": str(kpis['sessions']),
                "delta": None
            },
            {
                "title": "Śr. liczba serii / sesję",
                "value": f"{kpis['avg_sets_per_session']:.1f}",
                "delta": f"Δ {kpis['sets_change']}%"
            }
        ]
        
        columns = [col1, col2, col3, col4]
        
        for col, config in zip(columns, kpi_configs):
            with col:
                self._render_kpi_card(**config)
    
    def _render_kpi_card(self, title: str, value: str, delta: str = None):
        """Render individual KPI card"""
        delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else '<div class="kpi-delta" style="visibility:hidden;">—</div>'

        
        card_html = f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)