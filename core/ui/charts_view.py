import streamlit as st
import plotly.express as px
from ..styles.theme_manager import ThemeManager
import pandas as pd

class ChartsView:
    """Enhanced charts with Plotly integration"""
    
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
    
    def _display_intensity_chart(self, analytics):
        """Enhanced intensity chart with Plotly"""
        st.subheader("Średnia intensywność tygodniowa")
        
        df_intensity = analytics.df_sets.copy()
        
        if df_intensity.empty:
            st.info("Brak danych do wyświetlenia wykresu intensywności.")
            return
        
        df_intensity["Week"] = df_intensity["SessionDate"].dt.isocalendar().week
        df_intensity["Year"] = df_intensity["SessionDate"].dt.isocalendar().year

        weekly_intensity = (
        df_intensity.groupby(["Year", "Week"])["Intensity"]
        .mean()
        .reset_index()
        .sort_values(["Year", "Week"]))

        if weekly_intensity.empty:
            st.info("Brak danych do wyświetlenia wykresu intensywności.")
            return

        fig = px.line(
            weekly_intensity, 
            x="Week", 
            y="Intensity",
            title="Trend intensywności treningowej",
            markers=True,
            color_discrete_sequence=[self.colors.accent]
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.colors.text,
            title_font_size=16,
            xaxis_title="Tydzień roku",
            yaxis_title="Średnia intensywność",
            xaxis=dict(tickmode="linear", dtick=1),
        )
        
        st.plotly_chart(fig, width="stretch")
    
    def _display_volume_chart(self, analytics):
        """Enhanced volume chart with Plotly"""
        st.subheader("Łączna objętość tygodniowa")
        
        df_volume = analytics.df_sets.copy()
        df_volume["Week"] = df_volume["SessionDate"].dt.isocalendar().week
        df_volume["Year"] = df_volume["SessionDate"].dt.isocalendar().year
        
        weekly_volume = (
            df_volume.groupby(["Year", "Week"])["Volume"]
            .sum()
            .reset_index()
            .sort_values(["Year", "Week"])
        )
        
        if weekly_volume.empty:
            st.info("Brak danych do wyświetlenia wykresu objętości.")
            return
        
        fig = px.bar(
            weekly_volume,
            x="Week",
            y="Volume", 
            title="Objętość treningowa w czasie",
            color_discrete_sequence=[self.colors.accent_light]
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.colors.text,
            title_font_size=16
        )
        
        st.plotly_chart(fig, width="stretch")
    
    def render_exercise_1rm_chart(self, session_summary: pd.DataFrame, exercise_name: str):
        """Render 1RM trend chart for specific exercise"""
        st.subheader("Trend 1RM w czasie")
        
        fig = px.line(
            session_summary,
            x="SessionDate",
            y="Est1RM",
            markers=True,
            title=f"Szacowany 1RM dla: {exercise_name}",
            color_discrete_sequence=[self.colors.accent]
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.colors.text,
            title_font_size=16,
            xaxis_title="Data sesji",
            yaxis_title="Szacowany 1RM (kg)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_exercise_volume_chart(self, session_summary: pd.DataFrame, exercise_name: str):
        """Render training volume chart for specific exercise"""
        st.subheader("Objętość treningowa w czasie")
        
        fig = px.bar(
            session_summary,
            x="SessionDate",
            y="TotalVolume",
            title=f"Objętość treningowa dla: {exercise_name}",
            color_discrete_sequence=[self.colors.accent_light]
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color=self.colors.text,
            title_font_size=16,
            xaxis_title="Data sesji",
            yaxis_title="Objętość (Powtórz. × Ciężar, kg)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
