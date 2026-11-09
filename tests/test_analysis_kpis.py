"""Analysis snapshots preserve missing data and comparison boundaries."""

from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from metrics.plan_performance import compute_plan_performance
from test_plan_performance import AS_OF, data, execution


@pytest.mark.parametrize(
    "weight,rir,values,expected",
    [
        (60.0, 2, (10, 10, 9), "+2"),
        (65.0, 2, (10, 10, 9), "—"),
        (60.0, None, (10, 10, 9), "—"),
        (60.0, 2, (10, 10), "—"),
        (60.0, 2, (10, 9, 8), "+0"),
    ],
)
def test_exercise_change_uses_existing_comparability_rules(weight, rir, values, expected):
    rows = compute_plan_performance(
        data(
            execution(1, date(2026, 5, 4)),
            execution(2, date(2026, 5, 11), values, weight=weight, rir=rir),
        ),
        as_of=AS_OF,
    )
    app = AppTest.from_string("""
import streamlit as st
from ui.plan_adherence_view import PlanAdherenceView
PlanAdherenceView(manager=object()).render_performance(st.session_state['rows'])
""")
    app.session_state["rows"] = rows
    app.run()
    assert not app.exception
    assert app.metric[1].value == expected
    assert app.metric[2].value == f"{len(values)}/3"


def test_body_snapshot_tracks_selected_measurement_dates_and_missing_trend():
    app = AppTest.from_string("""
from datetime import date
from ui.body_metrics_view import BodyMetricsView
BodyMetricsView({'timeline': [
    {'date': date(2026, 5, 1), 'weight': 80., 'waist': 82.},
    {'date': date(2026, 5, 8), 'weight': 81.},
]}, manager=object()).render()
""").run()
    assert not app.exception
    assert [item.value for item in app.metric] == ["81 kg", "+1 kg", "08 May 2026"]
    app.selectbox(key="analysis_body_metric").select("Waist").run()
    assert not app.exception
    assert [item.value for item in app.metric] == ["82 cm", "—", "01 May 2026"]


@pytest.mark.parametrize(
    "targets,expected",
    [
        (None, ["5.0", "—", "—"]),
        ({"Chest": 0.0}, ["5.0", "0.0", "—"]),
        ({"Chest": 10.0}, ["5.0", "10.0", "50%"]),
    ],
)
def test_muscle_snapshot_handles_missing_and_zero_targets(targets, expected):
    app = AppTest.from_string("""
import pandas as pd
import streamlit as st
from ui.utils.muscle_distribution_table import render_weekly_distribution
render_weekly_distribution(pd.DataFrame([
    {'Body Part': 'Chest', 'Total_Sets': 10.},
    {'Body Part': 'Back', 'Total_Sets': 4.},
]), 2., 'Test period', weekly_targets=st.session_state['targets'])
""")
    app.session_state["targets"] = targets
    app.session_state["analysis_muscle_part"] = "Chest"
    app.run()
    assert not app.exception
    assert [item.value for item in app.metric] == expected
    app.selectbox(key="analysis_muscle_part").select("Back").run()
    assert not app.exception
    assert app.metric[0].value == "2.0"
    assert app.metric[2].value == "—"
