"""Exercise the calendar through real Streamlit reruns without a database."""

from streamlit.testing.v1 import AppTest


APP = '''
from unittest.mock import patch
import pandas as pd
import streamlit as st
from ui.dashboard_view import DashboardView

rows = [
    dict(session_id=1, session_date="2024-02-29", exercise_name="Bench Press",
         set_number=1, repetitions=10, weight=60., duration_seconds=None),
    dict(session_id=2, session_date="2024-02-29", exercise_name="Plank",
         set_number=1, repetitions=0, weight=0., duration_seconds=90),
    dict(session_id=3, session_date="2024-04-01", exercise_name="Row",
         set_number=1, repetitions=8, weight=40., duration_seconds=None),
]
df = pd.DataFrame(rows)
month = st.session_state.get("filter_month", "All time")
if month != "All time":
    df = df.loc[df.session_date.str.startswith(month)]
with patch("ui.dashboard_view.DataManager"):
    view = DashboardView({}, df, month)
view._render_history()
'''


def start_app(month="All time"):
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["filter_month"] = month
    app.run()
    assert not app.exception
    return app


def session_count(app):
    return sum(button.label == "Delete Session" for button in app.button)


def test_calendar_selects_day_and_shows_all_sessions_on_leap_day():
    app = start_app()
    assert session_count(app) == 1
    assert any("Sessions on 01 Apr 2024" in item.value for item in app.markdown)

    app.selectbox(key="history_month").select("2024-02").run()
    assert not app.exception
    assert app.button(key="history_date_2024-02-29").label == "29"
    assert "2 session(s)" in app.button(key="history_date_2024-02-29").help
    assert session_count(app) == 2
    assert {button.key for button in app.button if button.label == "Delete Session"} == {"del_1", "del_2"}
    assert any("1:30" in item.value for item in app.markdown)

    app.button(key="history_date_2024-02-28").click().run()
    assert not app.exception
    assert session_count(app) == 0
    assert app.info[0].value == "No sessions recorded for this day."

    app.button(key="history_date_2024-02-29").click().run()
    assert session_count(app) == 2


def test_empty_month_between_workouts_remains_browsable():
    app = start_app()
    app.selectbox(key="history_month").select("2024-03").run()
    assert not app.exception
    assert app.button(key="history_date_2024-03-31").label == "31"
    assert session_count(app) == 0
    assert app.info[0].value == "No sessions recorded for this day."


def test_sidebar_filter_controls_calendar_and_resets_visible_sessions():
    app = start_app("2024-02")
    assert len(app.selectbox) == 0
    assert session_count(app) == 2

    app.session_state["filter_month"] = "2024-04"
    app.run()
    assert not app.exception
    assert session_count(app) == 1
    assert any("Sessions on 01 Apr 2024" in item.value for item in app.markdown)

    app.session_state["filter_month"] = "2024-03"
    app.run()
    assert not app.exception
    assert session_count(app) == 0
    assert app.button(key="history_date_2024-03-01").label == "1"


def test_no_history_shows_empty_state():
    app = AppTest.from_string('''
from unittest.mock import patch
import pandas as pd
from ui.dashboard_view import DashboardView
with patch("ui.dashboard_view.DataManager"):
    view = DashboardView({}, pd.DataFrame())
view._render_history()
''', default_timeout=30).run()
    assert not app.exception
    assert app.info[0].value == "No workout history yet."
