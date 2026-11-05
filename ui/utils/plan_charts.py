"""Charts for linked training data; no claims about physiological effectiveness."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from metrics.load_metrics import describe_load, recorded_load, same_loads

from ui.utils.ui_helpers import ACCENT, MUTED, PLOTLY_LAYOUT, WARN


def weekly_execution_chart(weeks):
    fig = go.Figure()
    for key, label, color in (
        ("complete", "All sets logged", ACCENT), ("partial", "Partial", "#78d4d8"),
        ("unmatched", "No matching work", WARN), ("unlinked", "No linked log", "#59616d"),
    ):
        fig.add_bar(x=[row["week"] for row in weeks], y=[row[key] for row in weeks],
                    name=label, marker_color=color,
                    hovertemplate="Week of %{x|%d %b}<br>" + label + ": %{y}<extra></extra>")
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=290, barmode="stack", showlegend=True,
                      legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11)),
                      margin=dict(l=8, r=8, t=40, b=8))
    fig.update_yaxes(title_text="Workouts", dtick=1, rangemode="tozero")
    fig.update_xaxes(tickformat="%d %b", title_text="Week beginning")
    return fig


def exercise_history_chart(rows):
    points = {}
    for row in rows:
        if row["previous"]:
            points[row["previous"]["session_id"]] = row["previous"]
        if row["sets"]:
            points[row["session_id"]] = row
    points = list(points.values())  # Source rows already follow actual chronology.
    if not points:
        return None
    field = "seconds" if points[-1]["unit"] == "seconds" else "reps"
    with_load = any(recorded_load(item) or item.get("load_type", "legacy") != "legacy" for row in points for item in row["sets"])
    fig = make_subplots(rows=2 if with_load else 1, cols=1, shared_xaxes=True,
                        vertical_spacing=0.14 if with_load else 0)
    x = list(range(len(points)))
    labels = [f'{row["performed_on"]:%d %b}' for row in points]
    phases = [row.get("training_phase", "normal") for row in points]
    custom = [[row["performed_on"].isoformat(), len(row["sets"]), row["planned_sets"], row["session_id"], row["in_range"], phase,
               " / ".join(dict.fromkeys(describe_load(item) for item in row["sets"]))] for row, phase in zip(points, phases)]
    markers = dict(size=7, symbol=["diamond" if phase == "deload" else "circle" for phase in phases],
                   color=[WARN if phase == "deload" else ACCENT for phase in phases])
    values = [sum(item[field] for item in row["sets"]) / len(row["sets"]) for row in points]
    comparable = all(same_loads(old["sets"], new["sets"]) for old, new in zip(points, points[1:]))
    fig.add_trace(go.Scatter(x=x, y=values, mode="lines+markers" if comparable else "markers", line=dict(color=ACCENT),
                            marker=markers, customdata=custom,
                            hovertemplate="%{customdata[0]} · session #%{customdata[3]} · %{customdata[5]}<br>Mean: %{y:.1f}<br>Logged sets: %{customdata[1]}/%{customdata[2]}<br>In range: %{customdata[4]}/%{customdata[2]}<extra></extra>"), row=1, col=1)
    for index, point in enumerate(points):
        fig.add_shape(type="rect", x0=index - 0.5, x1=index + 0.5,
                      y0=point["target_min"], y1=point["target_max"], xref="x", yref="y", layer="below",
                      fillcolor="rgba(0,173,181,0.12)", line_color=ACCENT,
                      line_width=1 if point["target_min"] == point["target_max"] else 0, row=1, col=1)
    fig.update_yaxes(title_text=f"Mean {field} / set", row=1, col=1)
    if with_load:
        means = [None if any(recorded_load(item) is None for item in row["sets"]) else
                 sum(recorded_load(item) for item in row["sets"]) / len(row["sets"]) for row in points]
        kinds = {item.get("load_type", "legacy") for row in points for item in row["sets"]}
        fig.add_trace(go.Scatter(x=x, y=means, customdata=custom, connectgaps=False,
                                mode="lines+markers" if len(kinds) == 1 else "markers", line=dict(color=MUTED), marker=markers,
                                hovertemplate="%{customdata[6]}<br>Mean load: %{y:g} kg<extra></extra>"), row=2, col=1)
        fig.update_yaxes(title_text="Mean total / recorded kg", row=2, col=1)
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=350 if with_load else 250, margin=dict(l=8, r=8, t=16, b=8))
    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=labels, range=[-0.5, len(points) - 0.5])
    fig.update_xaxes(title_text="Recorded session", row=2 if with_load else 1, col=1)
    return fig
