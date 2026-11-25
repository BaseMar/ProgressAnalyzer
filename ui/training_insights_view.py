"""Render readable observations, supporting evidence and suggested actions."""

from html import escape

import streamlit as st

from ui.utils.ui_helpers import section_header


def render_training_insights(report, exercise_names=None, *, show_target_actions=True):
    names = exercise_names or {}
    section_header("What changed · what to do")
    if not report.annotations and not report.highlighted_annotations:
        st.caption(
            "No recorded comparisons in this period yet. Record another workout to compare results."
        )
        return
    highlights = report.highlighted_annotations
    remaining = [item for item in report.annotations if item not in highlights]
    visible = [*highlights, *remaining][: len(report.annotations)]
    for insight in visible:
        name = (
            names.get(insight.exercise_id, f"Exercise #{insight.exercise_id}")
            if insight.exercise_id
            else None
        )
        action = insight.action
        if not show_target_actions and insight.next_target:
            action = "Use the prescribed target in Next workout."
        if insight in highlights:
            _highlight(insight, name, action)
        else:
            title = f"{name}: {insight.observation}" if name else insight.observation
            _observation(title, insight.evidence, action)


def _highlight(insight, name, action):
    previous, current = insight.sources
    unit = current.sets[0].unit
    delta = current.total_quantity - previous.total_quantity
    sign = "+" if delta > 0 else "−"
    icon, label = (
        ("trending_up", "Largest improvement")
        if insight.code == "more_output"
        else ("search", "Result to review")
    )
    suffix = f"{insight.code}_{insight.exercise_id}"
    with st.container(key=f"overview_highlight_{suffix}", gap="xsmall"):
        with st.container(
            horizontal=True,
            vertical_alignment="center",
            gap="small",
            wrap=False,
            key=f"insight_heading_{suffix}",
        ):
            with st.container(key=f"insight_exercise_{suffix}", gap=None):
                st.markdown(f":material/{icon}: {label}", width="content")
                st.button(
                    name,
                    key=f"insight_history_{suffix}",
                    type="tertiary",
                    icon=":material/arrow_forward:",
                    icon_position="right",
                    wrap=True,
                    help="Open the full recorded history of this exercise in Analysis.",
                    on_click=_open_exercise_history,
                    args=(insight.exercise_id,),
                )
            st.markdown(
                f'<div class="insight-highlight-delta"><strong>{sign}{abs(delta):g}</strong> '
                f"<span>{escape(unit)}</span></div>",
                unsafe_allow_html=True,
                width="content",
            )
        comparison = "Same load and RIR" if unit == "reps" else "Same load"
        _observation(comparison, insight.evidence, action)


def _observation(title, evidence, action):
    st.markdown(
        '<div class="analysis-insight">'
        f"<strong>{escape(title)}</strong><br>{escape(evidence)}"
        f"<br><strong>{escape(action)}</strong></div>",
        unsafe_allow_html=True,
    )


def _open_exercise_history(exercise_id):
    from ui.sidebar_view import _set_selected_nav

    _set_selected_nav("Analysis")
    st.session_state["analysis_tab"] = "Exercises"
    st.session_state["analysis_recorded_exercise"] = exercise_id
    st.session_state["analysis_month"] = "All time"
    st.session_state["analysis_period_value"] = "All time"
