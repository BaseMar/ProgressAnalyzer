from __future__ import annotations

import pandas as pd
import streamlit as st

# Vega-Lite chart config 
_VEGA_CONFIG = {
    "background": "#222831",
    "axis": {
        "gridColor":   "rgba(255,255,255,0.06)",
        "domainColor": "rgba(255,255,255,0.10)",
        "tickColor":   "rgba(255,255,255,0.10)",
        "labelColor":  "#9aa0a6",
        "titleColor":  "#9aa0a6",
        "labelFont":   "sans-serif",
        "labelFontSize": 11,
    },
    "view": {"stroke": "transparent"},
}


# Helpers

def _fmt_num(value, decimals: int = 1) -> str:
    """Return value formatted with thin-space thousands separator."""
    if value is None:
        return "—"
    try:
        return f"{value:,.{decimals}f}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return "—"

def _section_header(title: str) -> None:
    """Render a labelled horizontal rule used as a section divider."""
    st.markdown(f'<div class="section-header"><span>{title}</span><div class="section-rule"></div></div>', unsafe_allow_html=True)

def _chart_label(text: str) -> None:
    """Render a small-caps chart title above a chart."""
    st.markdown(f'<p class="chart-label">{text}</p>', unsafe_allow_html=True)

def _line_chart(df: pd.DataFrame, y_col: str, height: int = 260) -> None:
    """Render a themed Vega-Lite line chart."""
    chart_df = df.reset_index()
    date_col = chart_df.columns[0]

    spec = {
        "config":  _VEGA_CONFIG,
        "width":   "container",
        "height":  height,
        "mark": {
            "type":        "line",
            "color":       "#00ADB5",
            "strokeWidth": 2,
            "point": {"filled": True, "color": "#00ADB5", "size": 40},
        },
        "encoding": {
            "x": {
                "field": date_col,
                "type":  "temporal",
                "axis":  {"format": "%b %d", "tickCount": 6},
            },
            "y": {
                "field": y_col,
                "type":  "quantitative",
                "axis":  {"tickCount": 5},
            },
        },
        "data": {"values": chart_df.to_dict(orient="records")},
    }

    st.vega_lite_chart(spec, width='stretch')

def _set_pills(ex_df: pd.DataFrame) -> str:
    """Return HTML string of set pill badges for one exercise."""
    return "".join(f'<span class="set-pill">{row["Repetitions"]} × {row["Weight"]:g} kg</span>'
        for _, row in ex_df.sort_values("SetNumber").iterrows())


# View

class DashboardView:
    def __init__(self, metrics: dict, sets_df: pd.DataFrame) -> None:
        self.metrics = metrics
        self.sets_df = sets_df

    def render(self) -> None:
        self._render_title()
        self._render_kpis()
        self._render_trends()
        self._render_history()

    # Private sections

    def _render_title(self) -> None:
        st.markdown(
            '<div class="page-eyebrow">Overview</div>'
            '<h1 class="page-title">Workout Dashboard</h1>',
            unsafe_allow_html=True,
        )

    def _render_kpis(self) -> None:
        g = self.metrics.get("sessions", {}).get("global", {})

        _section_header("Performance Snapshot")

        cols = st.columns(5)
        cols[0].metric("Avg Intensity", f"{_fmt_num(g.get('avg_intensity'), 1)} %" if g.get("avg_intensity") is not None else "—")
        cols[1].metric("Sessions / Week", _fmt_num(g.get("avg_sessions_per_week"), 1) if g.get("avg_sessions_per_week") else "—")
        cols[2].metric("Avg Volume / Session", f"{_fmt_num(g.get('avg_volume_per_session'), 0)} kg" if g.get("avg_volume_per_session") else "—")
        cols[3].metric("Avg Sets / Session", _fmt_num(g.get("avg_sets_per_session"), 1) if g.get("avg_sets_per_session")  else "—")
        cols[4].metric("Avg Duration", f"{_fmt_num(g.get('avg_session_duration'), 0)} min" if g.get("avg_session_duration")  else "—")

    def _render_trends(self) -> None:
        per_session = self.metrics.get("sessions", {}).get("per_session", {})

        rows = [
            {
                "Date": s["session_date"],
                "Volume (kg)": s.get("total_volume"),
                "Duration (min)": s.get("duration_minutes"),
            }
            for s in per_session.values()
            if s.get("session_date") is not None]

        _section_header("Session Trends")

        if not rows:
            st.info("No trend data available yet.")
            return

        trend_df = pd.DataFrame(rows).sort_values("Date").set_index("Date")
        col1, col2 = st.columns(2)

        with col1:
            _chart_label("Volume per Session")
            _line_chart(trend_df, "Volume (kg)")

        with col2:
            _chart_label("Session Duration")
            _line_chart(trend_df, "Duration (min)")

    def _render_history(self) -> None:
        _section_header("Session History")

        df = self.sets_df.copy()
        df["SessionDate"] = pd.to_datetime(df["SessionDate"])
        df = df.sort_values("SessionDate", ascending=False)

        for session_date, session_df in df.groupby("SessionDate", sort=False):
            total_volume = (session_df["Repetitions"] * session_df["Weight"]).sum()
            total_sets = len(session_df)
            exercises_count = session_df["ExerciseName"].nunique()
            volume_str = f"{total_volume:,.0f}".replace(",", "\u202f")

            label = (
                f"{session_date.strftime('%d %b %Y')}   ·   "
                f"{total_sets} sets   ·   "
                f"{exercises_count} exercises   ·   "
                f"{volume_str} kg"
            )

            with st.expander(label, icon=":material/event:"):
                for exercise, ex_df in session_df.groupby("ExerciseName"):
                    st.markdown(
                        f'<p class="exercise-label">{exercise}</p>'
                        f'<div class="set-pills">{_set_pills(ex_df)}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<hr class="exercise-divider">', unsafe_allow_html=True)
