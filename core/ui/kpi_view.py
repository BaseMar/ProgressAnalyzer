import streamlit as st

class KPIView:
    """
    Klasa odpowiedzialna za prezentację metryk KPI w dashboardzie.
    Oddziela warstwę wizualną (UI) od logiki obliczeniowej.
    """

    @staticmethod
    def display(kpis: dict):
        """Renderuje karty KPI w czterech kolumnach."""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Średnia intensywność</div>
                    <div class="kpi-value">{kpis['avg_intensity']:.1f} kg</div>
                    <div class="kpi-delta">Δ {kpis['intensity_change']}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Łączna objętość tygodniowa</div>
                    <div class="kpi-value">{f"{kpis['total_volume']:,.0f}".replace(",", " ")} kg</div>
                    <div class="kpi-delta">Δ {kpis['volume_change']}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Liczba sesji</div>
                    <div class="kpi-value">{kpis['sessions']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Śr. liczba serii / sesję</div>
                    <div class="kpi-value">{kpis['avg_sets_per_session']:.1f}</div>
                    <div class="kpi-delta">Δ {kpis['sets_change']}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )