import html as _html

import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Any, Optional

from ..styles.theme_manager import ThemeManager


class ChartsView:
    """Enhanced charts with Plotly integration (uses Analytics public methods)"""

    def __init__(self, theme: ThemeManager):
        self.theme: ThemeManager = theme
        self.colors = theme.colors

    def render(self, analytics):
        """Render main dashboard charts"""
        # `analytics` is a runtime analytics object exposing `weekly_agg_df` and similar.
        # We type it as Any to avoid heavy coupling in the UI layer.
        analytics: Any = analytics
        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            self._display_intensity_chart(analytics)

        with col2:
            self._display_volume_chart(analytics)

    def _apply_common_layout(
        self, fig: Any, xaxis_title: Optional[str] = None, yaxis_title: Optional[str] = None
    ) -> None:
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=self.colors.text,
            title_font_size=16,
        )
        if xaxis_title:
            fig.update_xaxes(title_text=xaxis_title)
        if yaxis_title:
            fig.update_yaxes(title_text=yaxis_title)

    # --- Main Dashboard Charts ---
    def _display_intensity_chart(self, analytics: Any) -> None:
        st.subheader("Average Weekly Intensity")

        weekly_intensity = analytics.weekly_agg_df("Intensity", "mean")

        if weekly_intensity.empty:
            st.info("No data available to display intensity chart.")
            return

        weekly_intensity = weekly_intensity.assign(
            Label=weekly_intensity["Year"].astype(str)
            + "-W"
            + weekly_intensity["Week"].astype(str)
        )

        fig = px.line(
            weekly_intensity,
            x="Label",
            y="Value",
            title="Training Intensity Trend",
            markers=True,
            color_discrete_sequence=[self.colors.accent],
        )

        self._apply_common_layout(
            fig,
            xaxis_title="Week (year-week)",
            yaxis_title="Average Intensity (%1RM)",
        )
        st.plotly_chart(fig, width="stretch")

    def _display_volume_chart(self, analytics: Any) -> None:
        """Enhanced volume chart with Plotly"""
        st.subheader("Total Weekly Volume")

        weekly_volume = analytics.weekly_agg_df("Volume", "sum")
        if weekly_volume.empty:
            st.info("No data available to display volume chart.")
            return

        weekly_volume = weekly_volume.assign(
            Label=weekly_volume["Year"].astype(str)
            + "-W"
            + weekly_volume["Week"].astype(str)
        )

        fig = px.bar(
            weekly_volume,
            x="Label",
            y="Value",
            title="Training Volume Over Time",
            color_discrete_sequence=[self.colors.accent_light],
        )

        self._apply_common_layout(
            fig, xaxis_title="Week (year-week)", yaxis_title="Volume (kg)"
        )
        st.plotly_chart(fig, width="stretch")

    # --- Exercise-specific Charts ---
    def render_exercise_1rm_chart(
        self, session_summary: pd.DataFrame, exercise_name: str
    ) -> None:
        """Render 1RM trend chart for specific exercise"""
        st.subheader("1RM Trend Over Time")
        if session_summary.empty:
            st.info("No data available for chart.")
            return

        fig = px.line(
            session_summary,
            x="SessionDate",
            y="Est1RM",
            markers=True,
            title=f"Estimated 1RM for: {exercise_name}",
            color_discrete_sequence=[self.colors.accent],
        )

        self._apply_common_layout(
            fig, xaxis_title="Session Date", yaxis_title="Estimated 1RM (kg)"
        )
        st.plotly_chart(fig, width="stretch")

    def render_exercise_volume_chart(
        self, session_summary: pd.DataFrame, exercise_name: str
    ) -> None:
        """Render training volume chart for specific exercise"""
        st.subheader("Training Volume Over Time")
        if session_summary.empty:
            st.info("No data available for chart.")
            return

        fig = px.bar(
            session_summary,
            x="SessionDate",
            y="TotalVolume",
            title=f"Training Volume for: {exercise_name}",
            color_discrete_sequence=[self.colors.accent_light],
        )

        self._apply_common_layout(
            fig,
            xaxis_title="Session Date",
            yaxis_title="Volume (Reps × Weight, kg)",
        )
        st.plotly_chart(fig, width="stretch")

    # --- Muscle Group Charts ---
    def render_muscle_volume_chart(self, muscles: Any) -> None:
        df = muscles.volume_chart_data()
        if df.empty:
            st.info("No data available for volume chart.")
            return

        fig = px.bar(
            df,
            x="BodyPart",
            y="total_volume",
            color="total_volume",
            color_continuous_scale="Viridis",
            title="Volume by Muscle Group",
        )

        self._apply_common_layout(
            fig, xaxis_title="Muscle Group", yaxis_title="Volume (kg)"
        )

        st.plotly_chart(fig, width="stretch", key=f"muscle_volume_{id(df)}")

    def render_muscle_intensity_chart(self, muscles: Any) -> None:
        df = muscles.intensity_chart_data()

        if df.empty:
            st.info("No data available for intensity chart.")
            return

        fig = px.bar(
            df,
            x="BodyPart",
            y="mean_intensity",
            title="Average Intensity by Muscle Group",
            color_discrete_sequence=[self.colors.accent_light],
        )

        self._apply_common_layout(
            fig, xaxis_title="Muscle Group", yaxis_title="Intensity (%1RM)"
        )
        st.plotly_chart(fig, width="stretch")

    def render_muscle_group_charts(self, muscles: Any) -> None:
        col1, col2 = st.columns(2)
        with col1:
            self.render_muscle_volume_chart(muscles)

        with col2:
            self.render_muscle_intensity_chart(muscles)

    def render_muscle_summary_table(self, muscles: Any) -> None:
        """Render an enhanced summary table for muscle groups with badges and trend indicators."""
        summary = muscles.muscle_groups_summary()

        if summary.empty:
            st.info("No data available for muscle group summary.")
            return

        # Prepare user-friendly columns: Load badge and trend text
        def _load_badge(level: str) -> str:
            mapping = {
                "too little": "🔻 too little",
                "OK": "✅ OK",
                "too much": "⚠️ too much",
                "no data": "❓ no data",
            }
            return mapping.get(level, str(level))

        def _trend_text(val: float) -> str:
            try:
                v = float(val)
            except Exception:
                return "—"
            if v > 0:
                return f"▲ {v:.1f}%"
            if v < 0:
                return f"▼ {abs(v):.1f}%"
            return "—"

        # prepare dataframe and display as themed HTML
        df = summary.copy()
        df["Load"] = df["load_level"].apply(_load_badge)
        df["Trend"] = df["trend_pct"].apply(_trend_text)

        # Format numeric columns
        df_display = df.copy()
        df_display["sessions_per_week"] = df_display["sessions_per_week"].map(
            lambda x: f"{x:.2f}"
        )
        df_display["avg_volume_per_session"] = df_display["avg_volume_per_session"].map(
            lambda x: f"{x:.0f}"
        )

        # Theme colors
        accent = self.colors.accent
        accent_light = self.colors.accent_light
        text = self.colors.text
        muted = self.colors.text_muted

        css = f"""<style>
.muscle-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: {self.theme.font_family};
    font-size: 14px;
    color: {text};
}}
.muscle-table th, .muscle-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    text-align: left;
}}
.muscle-table thead th {{
    color: {muted};
    font-weight: 600;
    background: transparent;
}}
.badge {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    color: #000000;
}}
.badge-ok {{ background: {accent_light}; color: #000; }}
.badge-low {{ background: #FF7A7A; color: #000; }}
.badge-high {{ background: #FFD27A; color: #000; }}
.trend-up {{ color: {accent}; font-weight:700 }}
.trend-down {{ color: #FF6B6B; font-weight:700 }}
.assessment {{ color: {muted}; font-size: 13px }}
</style>"""

        rows_html = []
        for _, r in df_display.iterrows():
            part = _html.escape(str(r["BodyPart"]))
            sessions = int(r["sessions_count"])
            spw = _html.escape(str(r["sessions_per_week"]))
            avg_vol = _html.escape(str(r["avg_volume_per_session"]))
            recommended = _html.escape(str(r["recommended_sessions"]))
            load_raw = r["load_level"]

            if load_raw == "OK":
                badge = f'<span class="badge badge-ok">OK</span>'
            elif load_raw == "too little":
                badge = f'<span class="badge badge-low">too little</span>'
            elif load_raw == "too much":
                badge = f'<span class="badge badge-high">too much</span>'
            else:
                badge = f'<span class="badge">{_html.escape(load_raw)}</span>'

            try:
                trend_val = float(r.get("trend_pct", 0.0))
            except Exception:
                trend_val = 0.0

            if trend_val > 0:
                trend_html = f'<span class="trend-up">▲ {trend_val:.1f}%</span>'
            elif trend_val < 0:
                trend_html = f'<span class="trend-down">▼ {abs(trend_val):.1f}%</span>'
            else:
                trend_html = "—"

            assessment = _html.escape(str(r.get("assessment", "")))

            row = (
                "<tr>"
                f"<td>{part}</td>"
                f"<td>{sessions}</td>"
                f"<td>{spw}</td>"
                f"<td style='text-align:right'>{avg_vol}</td>"
                f"<td>{recommended}</td>"
                f"<td>{badge}</td>"
                f"<td>{trend_html}</td>"
                f"<td class='assessment'>{assessment}</td>"
                "</tr>"
            )
            rows_html.append(row)

        # Trim any trailing whitespace so the '<table' starts at the beginning
        # of a line (avoids Markdown treating it as an indented code block).
        css = css.strip()

        table_html = (
            css
            + "<table class='muscle-table'><thead><tr>"
            + "<th>Muscle Group</th><th>Sessions</th><th>Sessions / Week</th><th>Avg Volume / Session (kg)</th><th>Recommended (sessions/week)</th><th>Load</th><th>Trend</th><th>Assessment</th>"
            + "</tr></thead><tbody>"
            + "".join(rows_html)
            + "</tbody></table>"
        )

        st.markdown(table_html, unsafe_allow_html=True)
