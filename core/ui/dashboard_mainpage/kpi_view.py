import streamlit as st
from typing import Optional, List, Dict, Any

from ...styles.theme_manager import ThemeManager


class KPIView:
    """Enhanced KPI display with better formatting"""

    def __init__(self, theme: ThemeManager) -> None:
        self.theme: ThemeManager = theme

    def display(self, kpi_cards: List[Dict[str, Any]]) -> None:
        """Render KPI cards given as a list of dicts with title, value, delta"""
        st.markdown("---")

        n_cols = min(len(kpi_cards), 4)
        columns = st.columns(n_cols)

        for col, card in zip(columns, kpi_cards):
            with col:
                self._render_kpi_card(
                    title=card.get("title", ""),
                    value=card.get("value", ""),
                    delta=card.get("delta"),
                )

    def _render_kpi_card(self, title: str, value: str, delta: Optional[str] = None) -> None:
        """Render individual KPI card"""
        delta_html = (
            f'<div class="kpi-delta">{delta}</div>'
            if delta
            else '<div class="kpi-delta" style="visibility:hidden;">—</div>'
        )
        card_html = f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
