import streamlit as st
import plotly.express as px
from ..styles.theme_manager import ThemeManager
import pandas as pd

class ChartsView:
    """Enhanced charts with Plotly integration (uses Analytics public methods)"""
    
    def __init__(self, theme: ThemeManager):
        self.theme = theme
        self.colors = theme.colors
    
    def render(self, analytics):
        """Render main dashboard charts"""
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            self._display_intensity_chart(analytics)
        
        with col2:
            self._display_volume_chart(analytics)
    
    def _apply_common_layout(self, fig, xaxis_title: str = None, yaxis_title: str = None):
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.colors.text,
            title_font_size=16,
        )
        if xaxis_title:
            fig.update_xaxes(title_text=xaxis_title)
        if yaxis_title:
            fig.update_yaxes(title_text=yaxis_title)

    # --- Main Dashboard Charts ---
    def _display_intensity_chart(self, analytics):
        st.subheader("Średnia intensywność tygodniowa")

        weekly_intensity = analytics.weekly_agg_df("Intensity", "mean")
        
        if weekly_intensity.empty:
            st.info("Brak danych do wyświetlenia wykresu intensywności.")
            return

        weekly_intensity = weekly_intensity.assign(Label=weekly_intensity["Year"].astype(str) + "-W" + weekly_intensity["Week"].astype(str))

        fig = px.line(
            weekly_intensity,
            x="Label",
            y="Value",
            title="Trend intensywności treningowej",
            markers=True,
            color_discrete_sequence=[self.colors.accent]
        )

        self._apply_common_layout(fig, xaxis_title="Tydzień (rok-tydzień)", yaxis_title="Średnia intensywność (%1RM)")
        st.plotly_chart(fig, width='stretch')
    
    def _display_volume_chart(self, analytics):
        """Enhanced volume chart with Plotly"""
        st.subheader("Łączna objętość tygodniowa")
        
        weekly_volume = analytics.weekly_agg_df("Volume", "sum")
        if weekly_volume.empty:
            st.info("Brak danych do wyświetlenia wykresu objętości.")
            return

        weekly_volume = weekly_volume.assign(Label=weekly_volume["Year"].astype(str) + "-W" + weekly_volume["Week"].astype(str))

        fig = px.bar(
            weekly_volume,
            x="Label",
            y="Value",
            title="Objętość treningowa w czasie",
            color_discrete_sequence=[self.colors.accent_light]
        )

        self._apply_common_layout(fig, xaxis_title="Tydzień (rok-tydzień)", yaxis_title="Objętość (kg)")
        st.plotly_chart(fig, width='stretch')
    
    # --- Exercise-specific Charts ---
    def render_exercise_1rm_chart(self, session_summary: pd.DataFrame, exercise_name: str):
        """Render 1RM trend chart for specific exercise"""
        st.subheader("Trend 1RM w czasie")
        if session_summary.empty:
            st.info("Brak danych do wykresu.")
            return

        fig = px.line(
            session_summary,
            x="SessionDate",
            y="Est1RM",
            markers=True,
            title=f"Szacowany 1RM dla: {exercise_name}",
            color_discrete_sequence=[self.colors.accent]
        )
        
        self._apply_common_layout(fig, xaxis_title="Data sesji", yaxis_title="Szacowany 1RM (kg)")
        st.plotly_chart(fig, width='stretch')
    
    def render_exercise_volume_chart(self, session_summary: pd.DataFrame, exercise_name: str):
        """Render training volume chart for specific exercise"""
        st.subheader("Objętość treningowa w czasie")
        if session_summary.empty:
            st.info("Brak danych do wykresu.")
            return

        fig = px.bar(
            session_summary,
            x="SessionDate",
            y="TotalVolume",
            title=f"Objętość treningowa dla: {exercise_name}",
            color_discrete_sequence=[self.colors.accent_light]
        )
        
        self._apply_common_layout(fig, xaxis_title="Data sesji", yaxis_title="Objętość (Powtórz. × Ciężar, kg)")
        st.plotly_chart(fig, width='stretch')
