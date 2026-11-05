"""A local analysis filter, independent of Overview and future targets."""
from datetime import date

import pandas as pd
import streamlit as st
from metrics.body_metrics import to_date


def select_analysis_month(input_data):
    dates = [item.session_date for item in input_data.sessions]
    dates += [item.date for item in input_data.body_measurements]
    dates += [item.date for item in input_data.body_composition]
    dates.append(date.today())
    dates = [to_date(value) for value in dates]
    months = [str(value) for value in pd.period_range(min(dates), max(dates), freq="M")]
    choices = ["All time", *reversed(months)]
    key = "analysis_month"
    if st.session_state.get(key) not in choices:
        saved = st.session_state.get("analysis_period_value")
        st.session_state[key] = saved if saved in choices else "All time"
    selected = st.selectbox("Analysis period", choices, key=key,
                            format_func=lambda value: value if value == "All time" else date.fromisoformat(value + "-01").strftime("%B %Y"))
    st.session_state["analysis_period_value"] = selected
    return selected
