"""A compact starting view with separate, auditable exercise trend rankings."""

from collections import Counter
from html import escape
from textwrap import wrap

import plotly.graph_objects as go
import streamlit as st

from metrics.progress_ranking import rank_exercise_progress, ranking_groups
from ui.utils.ui_helpers import ACCENT, MUTED, PLOTLY_LAYOUT, TEXT, WARN


def render_progress_ranking(exercise_metrics, *, filters):
    report = rank_exercise_progress(exercise_metrics)
    measures = [
        name
        for name in ("Estimated strength", "Hold time")
        if any(item.measure == name for item in report.trends)
    ]
    if not measures:
        st.info(
            "Not enough comparable sessions for a ranking in this period. Open Exercises for the full recorded history, or change Analysis period above the tabs."
        )
        st.caption(
            "Strength estimates need at least two eligible external-load sessions with one load convention. Bodyweight strength is excluded; timed holds need a known, unchanged load."
        )
        return
    measure = measures[0]
    if len(measures) > 1:
        with filters:
            if st.session_state.get("analysis_ranking_measure") not in measures:
                st.session_state["analysis_ranking_measure"] = measure
            measure = st.selectbox("Ranking measure", measures, key="analysis_ranking_measure")
    trends = tuple(item for item in report.trends if item.measure == measure)
    top, bottom = ranking_groups(trends)
    st.subheader("Top 5 / Bottom 5")
    st.caption(
        f"{measure} · first versus last windows of up to 3 sessions in this period. Open Exercises to inspect a full history."
    )
    with st.container(key="analysis_rankings"):
        columns = st.columns(2, gap="large")
        for column, title, items, message in (
            (columns[0], "Top 5 · largest increases", top, "No increases in this period."),
            (
                columns[1],
                "Bottom 5 · lowest changes",
                bottom,
                "No decreases or unchanged results in this period.",
            ),
        ):
            with column:
                st.markdown(f"**{title}**")
                if items:
                    st.plotly_chart(
                        ranking_chart(items),
                        width="stretch",
                        key=f"ranking_{'top' if items is top else 'bottom'}",
                    )
                else:
                    st.info(message)
    st.caption(
        f"{len(trends)} exercises with usable history. {len(report.unavailable_exercise_ids)} without a comparable trend in either measure. "
        "Bottom 5 includes decreases and unchanged results; missing data is excluded."
    )


def ranking_chart(items):
    names = Counter(item.name for item in items)
    labels = [
        "<br>".join(
            escape(part)
            for part in wrap(
                item.name + (f" · #{item.exercise_id}" if names[item.name] > 1 else ""),
                width=20,
                max_lines=3,
                placeholder="…",
            )
        )
        for item in items
    ]
    values = [item.change_pct for item in items]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=[str(item.exercise_id) for item in items],
            orientation="h",
            marker_color=[
                ACCENT if value > 0 else WARN if value < 0 else MUTED for value in values
            ],
            text=[f"{value:+.2f}%" for value in values],
            textposition="outside",
            textfont=dict(color=TEXT, size=13),
            cliponaxis=False,
            customdata=[
                [escape(item.name), item.baseline, item.current, item.sessions, item.window]
                for item in items
            ],
            hovertemplate="<b>%{customdata[0]}</b><br>Change: %{x:+.2f}%<br>First window: %{customdata[1]:.2f}<br>Last window: %{customdata[2]:.2f}<br>%{customdata[3]} sessions · %{customdata[4]} per window<extra></extra>",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(
        height=max(230, 100 + 64 * len(items)), margin=dict(l=140, r=54, t=16, b=48), bargap=0.4
    )
    extent = max(max(abs(value) for value in values), 1)
    fig.update_xaxes(
        title_text="Change (%)",
        ticksuffix="%",
        nticks=4,
        range=[-extent * 1.4, 0]
        if min(values) < 0
        else [-1, 1]
        if max(values) == 0
        else [0, extent * 1.4],
        zeroline=True,
    )
    fig.update_yaxes(
        type="category",
        categoryorder="array",
        categoryarray=[str(item.exercise_id) for item in items],
        tickmode="array",
        tickvals=[str(item.exercise_id) for item in items],
        ticktext=labels,
        autorange="reversed",
        tickfont=dict(color=TEXT, size=13),
        showgrid=False,
    )
    return fig
