"""Quantity and load charts with separate series for comparable set loads."""

from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from metrics.load_metrics import describe_load
from ui.utils.ui_helpers import ACCENT, MUTED, PLOTLY_LAYOUT


def load_history_chart(points, *, workload=False):
    points = [item for item in points if workload or item["eligible"]]
    if not points:
        return None
    sessions = defaultdict(list)
    for item in points:
        sessions[item["session_id"]].append(item)
    ordered = sorted(
        sessions,
        key=lambda sid: (
            pd.Timestamp(sessions[sid][0]["date"]),
            sessions[sid][0].get("session_order", sid),
        ),
    )
    timed = points[0]["unit"] == "seconds"
    legacy = points[0]["load_type"] == "legacy"
    fig = make_subplots(rows=1 if workload else 2, cols=1, shared_xaxes=True, vertical_spacing=0.14)
    x = list(range(len(ordered)))
    custom = [
        f"Session #{sid}<br>" + "<br>".join(describe_load(item) for item in sessions[sid])
        for sid in ordered
    ]
    if workload:
        values = []
        for sid in ordered:
            rows = sessions[sid]
            values.append(
                sum(item["quantity"] for item in rows)
                if timed
                else None
                if any(item["total_load_kg"] is None for item in rows)
                else sum(item["quantity"] * item["total_load_kg"] for item in rows)
            )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=values,
                mode="lines+markers",
                connectgaps=False,
                line=dict(color=ACCENT),
                customdata=custom,
                hovertemplate="%{customdata}<br>Workload: %{y:g}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.update_yaxes(
            title_text="Total seconds" if timed else "Volume load (kg × reps)", row=1, col=1
        )
    else:
        loads = sorted(
            {item["total_load_kg"] for item in points if item["total_load_kg"] is not None}
        )
        if any(item["total_load_kg"] is None for item in points):
            loads.append(None)
        for load in loads:
            values = [
                max(
                    (item["quantity"] for item in sessions[sid] if item["total_load_kg"] == load),
                    default=None,
                )
                for sid in ordered
            ]
            name = (
                "Unknown load"
                if load is None
                else f"{load:g} kg {'recorded' if legacy else 'total'}"
            )
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=values,
                    name=name,
                    mode="markers" if load is None else "lines+markers",
                    connectgaps=False,
                    customdata=custom,
                    hovertemplate="%{customdata}<br>Best set: %{y:g}<extra>%{fullData.name}</extra>",
                ),
                row=1,
                col=1,
            )
        means = [
            None
            if any(item["total_load_kg"] is None for item in sessions[sid])
            else sum(item["total_load_kg"] for item in sessions[sid]) / len(sessions[sid])
            for sid in ordered
        ]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=means,
                mode="lines+markers",
                connectgaps=False,
                line=dict(color=MUTED),
                name="Mean load",
                showlegend=False,
                customdata=custom,
                hovertemplate="%{customdata}<br>Mean load: %{y:g} kg<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(
            title_text="Best seconds / set" if timed else "Best reps / set", row=1, col=1
        )
        fig.update_yaxes(title_text="Recorded kg" if legacy else "Total load (kg)", row=2, col=1)
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(
        height=280 if workload else 420, showlegend=not workload, margin=dict(l=8, r=8, t=20, b=8)
    )
    labels = [f"{pd.Timestamp(sessions[sid][0]['date']):%d %b} · #{sid}" for sid in ordered]
    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=labels)
    return fig
