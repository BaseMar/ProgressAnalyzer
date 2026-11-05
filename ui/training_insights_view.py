"""Render prepared observations; evidence stays behind one disclosure."""
from dataclasses import asdict
from html import escape
import json

import streamlit as st

from ui.utils.ui_helpers import section_header


def render_training_insights(report, exercise_names=None, *, show_target_actions=True):
    names = exercise_names or {}
    section_header("What changed · what to do")
    if not report.annotations:
        st.caption("No recorded comparisons in this period yet. Link a session to start.")
        return
    for insight in report.annotations:
        name = names.get(insight.exercise_id, f"Exercise #{insight.exercise_id}") if insight.exercise_id else None
        title = f"{name}: {insight.observation}" if name else insight.observation
        action = insight.action
        if not show_target_actions and insight.next_target:
            action = "Use the prescribed target in Next workout."
        st.markdown('<div class="analysis-insight">'
                    f'<strong>{escape(title)}</strong><br>{escape(insight.evidence)}'
                    f'<br><strong>{escape(action)}</strong></div>', unsafe_allow_html=True)
        with st.expander(f"Why? · {title}"):
            st.caption(f"Evidence: {insight.evidence_level} · Rule: {insight.code}")
            st.caption(insight.rule)
            st.caption("Source snapshots include session IDs, actual dates, individual sets, targets and automatic interpretation. Unknown effort is never filled with zero.")
            st.json(json.dumps(asdict(insight), default=str, ensure_ascii=False), expanded=False)
    st.caption(f"{report.assessed_contexts} paired exercise contexts · {report.limited_contexts} with limited evidence. "
               + (f"Showing {len(report.annotations)} highest-priority annotations; {report.omitted_annotations} others are omitted here. " if report.omitted_annotations else "")
               + "These observations do not measure technique or muscle growth.")
