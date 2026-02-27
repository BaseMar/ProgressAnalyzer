"""
ui/utils/ui_helpers.py

Shared UI utilities for all views.
- Vega-Lite chart theme config
- Common render helpers (section header, chart label, line chart)
- Number formatter
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

# ── Vega-Lite theme ──────────────────────────────────────────
# These values live here — not in CSS — because they are passed
# directly into the Vega-Lite JS renderer which CSS cannot reach.
VEGA_CONFIG: dict = {
    "background": "#222831",
    "axis": {
        "gridColor":     "rgba(255,255,255,0.06)",
        "domainColor":   "rgba(255,255,255,0.10)",
        "tickColor":     "rgba(255,255,255,0.10)",
        "labelColor":    "#9aa0a6",
        "titleColor":    "#9aa0a6",
        "labelFont":     "sans-serif",
        "labelFontSize": 11,
    },
    "view": {"stroke": "transparent"},
}

# ── Design tokens — single source of truth for Python code ──────────────────
# main.css owns these for HTML/CSS. Plotly and other canvas-based renderers
# cannot read CSS, so we redeclare them here. Any palette change needs
# updating in BOTH main.css (:root) AND here.
ACCENT   = "#00ADB5"
SURFACE  = "#393E46"
BG       = "#222831"
WARN     = "#ffc947"
DANGER   = "#ff8585"
TEXT     = "#EEEEEE"
MUTED    = "#9aa0a6"
BORDER   = "rgba(255,255,255,0.07)"
GRID     = "rgba(255,255,255,0.06)"

# ── Plotly layout — apply with fig.update_layout(**PLOTLY_LAYOUT) ─────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor = BG,
    plot_bgcolor  = BG,
    font          = dict(color=TEXT, family="sans-serif", size=12),
    xaxis         = dict(gridcolor=GRID, linecolor=BORDER, tickcolor=BORDER, tickfont=dict(color=MUTED, size=11)),
    yaxis         = dict(gridcolor=GRID, linecolor=BORDER, tickcolor=BORDER, tickfont=dict(color=MUTED, size=11)),
    margin        = dict(l=8, r=8, t=36, b=8),
    title_font    = dict(color=MUTED, size=11, family="sans-serif"),
    showlegend    = False,
)

def fmt_num(value, decimals: int = 1) -> str:
    """Return value formatted with thin-space thousands separator."""
    if value is None:
        return "—"
    try:
        return f"{value:,.{decimals}f}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return "—"

def section_header(title: str) -> None:
    """Render a labelled horizontal rule as a section divider."""
    st.markdown(
        f'<div class="section-header">'
        f'<span>{title}</span>'
        f'<div class="section-rule"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def chart_label(text: str) -> None:
    """Render a small-caps label above a chart."""
    st.markdown(f'<p class="chart-label">{text}</p>', unsafe_allow_html=True)

def page_title(eyebrow: str, title: str) -> None:
    """Render a teal eyebrow label + h1 page title."""
    st.markdown(
        f'<div class="page-eyebrow">{eyebrow}</div>'
        f'<h1 class="page-title">{title}</h1>',
        unsafe_allow_html=True,
    )

def line_chart(
    df: pd.DataFrame,
    y_col: str,
    height: int = 260,
    x_type: str = "temporal",
    x_format: str = "%b %d",
) -> None:
    """
    Render a themed Vega-Lite line chart.

    Parameters
    ----------
    df       : DataFrame with the index used as the x-axis.
    y_col    : Column name for the y-axis.
    height   : Chart height in pixels.
    x_type   : Vega encoding type for x-axis ('temporal' or 'quantitative').
    x_format : Axis tick format string (used when x_type is 'temporal').
    """
    chart_df = df.reset_index()
    x_col = chart_df.columns[0]

    x_axis = {"tickCount": 6}
    if x_type == "temporal":
        x_axis["format"] = x_format

    spec = {
        "config": VEGA_CONFIG,
        "width":  "container",
        "height": height,
        "mark": {
            "type": "line",
            "color": ACCENT,
            "strokeWidth": 2,
            "point": {"filled": True, "color": ACCENT, "size": 40},
        },
        "encoding": {
            "x": {"field": x_col, "type": x_type, "axis": x_axis},
            "y": {"field": y_col, "type": "quantitative", "axis": {"tickCount": 5}},
        },
        "data": {"values": chart_df.to_dict(orient="records")},
    }

    st.vega_lite_chart(spec, width='stretch')
    