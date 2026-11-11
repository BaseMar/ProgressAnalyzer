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


def mean_load_history_chart(points):
    """Describe all logged sets, keeping incompatible load conventions separate."""
    if not points:
        return None
    sessions = defaultdict(list)
    for point in points:
        sessions[point["session_id"]].append(point)
    ordered = sorted(sessions, key=lambda sid: (pd.Timestamp(sessions[sid][0]["date"]), sid))
    timed = points[0]["unit"] == "seconds"
    kinds = list(dict.fromkeys(point["load_type"] for point in points))
    quantity_label = "Mean seconds / set" if timed else "Mean reps / set"
    load_label = (
        "Mean recorded load (kg)"
        if kinds == ["legacy"]
        else "Mean total / recorded load (kg)"
        if "legacy" in kinds
        else "Mean total load (kg)"
    )
    names = {
        "legacy": "Recorded kg",
        "external": "External kg",
        "bodyweight": "Bodyweight + load",
        "assisted_bodyweight": "Assisted bodyweight",
    }
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.16)
    x = list(range(len(ordered)))
    labels = [
        f"{pd.Timestamp(sessions[sid][0]['date']):%d %b %Y} - session #{sid}" for sid in ordered
    ]
    for kind in kinds:
        quantities, loads = [], []
        for sid in ordered:
            rows = [point for point in sessions[sid] if point["load_type"] == kind]
            quantities.append(sum(row["quantity"] for row in rows) / len(rows) if rows else None)
            loads.append(
                None
                if not rows or any(row["total_load_kg"] is None for row in rows)
                else sum(row["total_load_kg"] for row in rows) / len(rows)
            )
        for row, values, label, color in (
            (1, quantities, quantity_label, ACCENT),
            (2, loads, load_label, MUTED),
        ):
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=values,
                    name=names.get(kind, kind) if len(kinds) > 1 else label,
                    legendgroup=kind,
                    showlegend=len(kinds) > 1 and row == 1,
                    mode="lines+markers",
                    connectgaps=False,
                    line=dict(
                        color=color,
                        dash={
                            "legacy": "dot",
                            "external": "solid",
                            "bodyweight": "dash",
                            "assisted_bodyweight": "dashdot",
                        }.get(kind, "solid")
                        if len(kinds) > 1
                        else "solid",
                    ),
                    customdata=labels,
                    hovertemplate="%{customdata}<br>"
                    + names.get(kind, kind)
                    + "<br>"
                    + label
                    + ": %{y:.1f}<extra></extra>",
                ),
                row=row,
                col=1,
            )
    fig.update_yaxes(title_text=quantity_label, row=1, col=1)
    fig.update_yaxes(title_text=load_label, row=2, col=1)
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=420, margin=dict(l=8, r=8, t=20, b=8), showlegend=len(kinds) > 1)
    step = max(1, (len(x) + 4) // 5)
    ticks = sorted(set([*x[::step], x[-1]]))
    fig.update_xaxes(
        tickmode="array",
        tickvals=ticks,
        ticktext=[f"{pd.Timestamp(sessions[ordered[i]][0]['date']):%d %b}" for i in ticks],
    )
    fig.update_xaxes(title_text="Recorded session", row=2, col=1)
    return fig
