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
    if highlights:
        st.caption("Highlights use relative changes in reps or time at unchanged load and reserve.")
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
            label = "Largest improvement" if insight.code == "more_output" else "Result to review"
            with st.container(key=f"overview_highlight_{insight.code}_{insight.exercise_id}"):
                with st.container(
                    horizontal=True,
                    vertical_alignment="center",
                    gap="small",
                    wrap=True,
                    key=f"insight_heading_{insight.code}_{insight.exercise_id}",
                ):
                    st.markdown(
                        f'<div class="insight-highlight-label">{label}</div>',
                        unsafe_allow_html=True,
                        width="content",
                    )
                    st.button(
                        name,
                        key=f"insight_history_{insight.code}_{insight.exercise_id}",
                        type="tertiary",
                        icon=":material/arrow_forward:",
                        icon_position="right",
                        wrap=True,
                        help="Open the full recorded history of this exercise in Analysis.",
                        on_click=_open_exercise_history,
                        args=(insight.exercise_id,),
                    )
                _observation(insight.observation, insight.evidence, action)
        else:
            title = f"{name}: {insight.observation}" if name else insight.observation
            _observation(title, insight.evidence, action)
    st.caption(
        f"{report.assessed_contexts} exercise comparisons · {report.limited_contexts} awaiting comparable data. "
        + (
            f"Showing {len(visible)} observations; {report.omitted_annotations} others are omitted here. "
            if report.omitted_annotations
            else ""
        )
        + "These observations do not measure technique or muscle growth."
    )


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
    st.session_state["analysis_question"] = "Exercise progress"
    st.session_state["analysis_recorded_exercise"] = exercise_id
    st.session_state["analysis_month"] = "All time"
    st.session_state["analysis_period_value"] = "All time"
