"""Exercise comparison and estimated-strength sections below recorded history."""

from calendar import monthrange
from datetime import date
from itertools import zip_longest
from math import isfinite

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from metrics.load_metrics import describe_load
from metrics.progress_ranking import rank_exercise_progress
from metrics.recorded_progress import compare_recorded_exercise
from metrics.utils.dates import to_date
from ui.utils.ui_helpers import ACCENT, PLOTLY_LAYOUT


def render_latest_comparison(input_data, exercise_id, selected_month, *, as_of=None):
    """Show the actual latest pair, including evidence that prevents a verdict."""
    st.subheader("Latest comparison")
    if input_data is None:
        st.info("Open this exercise from Analysis to compare its recorded sessions.")
        return
    start = end = None
    if selected_month not in (None, "All time"):
        start = date.fromisoformat(f"{selected_month}-01")
        end = start.replace(day=monthrange(start.year, start.month)[1])
    insight = compare_recorded_exercise(
        input_data, exercise_id, as_of=as_of or date.today(), start=start, end=end
    )
    if insight is None:
        st.info("No recorded execution for this exercise in the selected period through today.")
        return
    if insight.code == "limited_evidence":
        st.info(insight.evidence)
    else:
        st.write(insight.observation)
    sources = insight.sources
    previous = sources[0] if len(sources) == 2 else None
    latest = sources[-1]
    timed = bool(latest.sets) and all(item.unit == "seconds" for item in latest.sets)
    # Quantity verdicts use the shared comparison, never a second interpretation.
    if insight.code in ("more_output", "less_output", "same_output"):
        change = sum(item.quantity for item in latest.sets) - sum(
            item.quantity for item in previous.sets
        )
        st.metric("Seconds vs previous" if timed else "Reps vs previous", f"{change:+g}")
    previous_label = (
        f"Previous · {previous.performed_on:%d %b %Y}" if previous else "Previous · unavailable"
    )
    latest_label = f"Latest · {latest.performed_on:%d %b %Y}"
    rows = [
        {
            "Working set": index,
            previous_label: _set_snapshot(old),
            latest_label: _set_snapshot(new),
        }
        for index, (old, new) in enumerate(
            zip_longest(previous.sets if previous else (), latest.sets), 1
        )
    ]
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _set_snapshot(item):
    if item is None:
        return "—"
    timed = item.unit == "seconds"
    try:
        load = describe_load(vars(item))
    except (TypeError, ValueError):
        load = "Unknown recorded load"
    value = f"{load} × {_number_text(item.quantity)} {'s' if timed else 'reps'}"
    if not timed:
        value += " · RIR " + _number_text(item.rir)
    return value


def _number_text(value):
    return (
        f"{value:g}"
        if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        else "?"
    )


def render_estimated_strength(exercise_id, exercise, *, as_of=None):
    """Reuse the eligible session estimates and the ranking's window calculation."""
    st.subheader("Estimated strength")
    cutoff = as_of or date.today()
    dynamic = [
        point
        for point in exercise.get("per_set_performance", ())
        if point["unit"] == "reps" and to_date(point["date"]) <= cutoff
    ]
    if len({point["load_type"] for point in dynamic}) > 1:
        st.info(
            "This period contains different load conventions. Choose a period with one "
            "convention to inspect its estimated-strength trend."
        )
        return
    points = [
        point for point in exercise.get("per_session_1rm", ()) if to_date(point["date"]) <= cutoff
    ]
    if not points:
        st.info("No eligible external-load strength estimates in this period.")
        return
    ranking = rank_exercise_progress(
        {
            "per_exercise": {
                exercise_id: {
                    **exercise,
                    "per_session_1rm": points,
                    "strength_trend_1rm": points[-1]["estimated_1rm"] - points[0]["estimated_1rm"]
                    if len(points) > 1
                    else None,
                }
            }
        }
    )
    trend = next((item for item in ranking.trends if item.measure == "Estimated strength"), None)
    latest, change, sessions = st.columns(3)
    latest.metric(
        "Latest eligible e1RM",
        f"{points[-1]['estimated_1rm']:g} kg",
        help=f"{to_date(points[-1]['date']):%d %b %Y} · session #{points[-1]['session_id']}",
    )
    change.metric(
        "Change between windows",
        f"{trend.change_pct:+.2f}%" if trend else "—",
    )
    sessions.metric("Sessions with estimates", str(len(points)))
    st.plotly_chart(_strength_chart(points), width="stretch", key="exercise_estimated_strength")
    if not trend:
        st.caption("One eligible session; at least two are needed for a trend.")


def _strength_chart(points):
    fig = go.Figure(
        go.Scatter(
            x=list(range(len(points))),
            y=[point["estimated_1rm"] for point in points],
            mode="lines+markers",
            line=dict(color=ACCENT),
            connectgaps=False,
            customdata=[
                [to_date(point["date"]).isoformat(), point["session_id"]] for point in points
            ],
            hovertemplate="%{customdata[0]} · session #%{customdata[1]}<br>"
            "Estimated 1RM: %{y:g} kg<extra></extra>",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=340, margin=dict(l=8, r=8, t=16, b=48))
    step = max(1, (len(points) + 4) // 5)
    ticks = sorted({*range(0, len(points), step), len(points) - 1})
    fig.update_xaxes(
        title_text="Recorded session",
        tickmode="array",
        tickvals=ticks,
        ticktext=[f"{to_date(points[index]['date']):%d %b}" for index in ticks],
    )
    fig.update_yaxes(title_text="Estimated 1RM (kg)")
    return fig
