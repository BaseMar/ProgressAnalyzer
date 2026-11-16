"""Navigation loaders clean up on success, errors and Streamlit control flow."""

import pytest
from streamlit.testing.v1 import AppTest

from ui.loading_view import loading_screen, update_loading_screen


class Placeholder:
    def __init__(self):
        self.markup = []
        self.cleared = 0

    def html(self, markup):
        self.markup.append(markup)

    def empty(self):
        self.cleared += 1


@pytest.fixture
def placeholders(monkeypatch):
    slots = []

    def empty():
        slot = Placeholder()
        slots.append(slot)
        return slot

    monkeypatch.setattr("ui.loading_view.st.empty", empty)
    return slots


def test_loading_status_escapes_text_updates_real_stages_and_clears(placeholders):
    with loading_screen("Loading <Analysis>", "History & plan"):
        assert placeholders[0].markup[-1].startswith("<style>")
        assert "position: fixed" in placeholders[0].markup[-1]
        assert 'role="status"' in placeholders[0].markup[-1]
        assert "Loading &lt;Analysis&gt;" in placeholders[0].markup[-1]
        assert "History &amp; plan" in placeholders[0].markup[-1]
        update_loading_screen("Preparing view")
        assert "Preparing view" in placeholders[0].markup[-1]
    assert placeholders[0].cleared == 1
    update_loading_screen("Finished")
    assert len(placeholders[0].markup) == 2


def test_disabled_loader_keeps_its_slot_without_showing_an_overlay(placeholders):
    with loading_screen("Updating a form", enabled=False) as screen:
        assert screen is None
        update_loading_screen("Unrelated form edit")
    assert len(placeholders) == 1 and not placeholders[0].markup


def test_nested_loading_uses_one_screen_without_removing_the_parent(placeholders):
    with loading_screen("Starting application") as outer:
        with loading_screen("Loading Analysis", "Preparing exercises") as inner:
            assert inner is outer
            assert "Preparing exercises" in placeholders[0].markup[-1]
            assert not placeholders[1].markup
        assert placeholders[0].cleared == 0
    assert placeholders[0].cleared == 1


class StopRendering(BaseException):
    pass


@pytest.mark.parametrize("exception", [RuntimeError, StopRendering])
def test_errors_and_stop_control_flow_always_remove_the_screen(placeholders, exception):
    with pytest.raises(exception):
        with loading_screen("Opening page"):
            with loading_screen("Opening section"):
                raise exception("Stop")
    assert placeholders[0].cleared == 1
    with loading_screen("Retry"):
        assert "Retry" in placeholders[-1].markup[-1]
    assert placeholders[-1].cleared == 1


ROUTE_APP = """
from contextlib import contextmanager
from unittest.mock import patch
import streamlit as st
import streamlit_app
from ui.loading_view import loading_screen

st.checkbox('Fail next page', key='test_failure')
@contextmanager
def tracked(title, detail, *, enabled):
    st.session_state.setdefault('loading_events', []).append((title, enabled))
    with loading_screen(title, detail, enabled=enabled) as screen:
        yield screen
def render(page):
    if st.session_state['test_failure']:
        st.error('Synthetic load failure')
        st.stop()
    st.write('Ready: ' + page)
with patch.object(streamlit_app, '_render_page', render), patch.object(streamlit_app, 'loading_screen', tracked):
    streamlit_app.main()
"""


def test_route_loader_runs_at_startup_and_navigation_but_not_ordinary_reruns():
    app = AppTest.from_string(ROUTE_APP).run()
    assert not app.exception and not app.error
    assert app.session_state["loading_events"][-1] == ("Loading Overview", True)
    assert app.session_state["_loaded_route"] == "Overview"
    app.run()
    assert app.session_state["loading_events"][-1] == ("Loading Overview", False)
    app.button(key="nav_Analysis").click().run()
    assert not app.exception and not app.error
    assert app.session_state["loading_events"][-1] == ("Loading Analysis", True)
    assert app.session_state["_loaded_route"] == "Analysis"
    assert all("app-loading-screen" not in item.proto.body for item in app.get("html"))


def test_failed_page_does_not_keep_a_loading_screen_or_mark_the_route_ready():
    app = AppTest.from_string(ROUTE_APP).run()
    app.checkbox(key="test_failure").check().run()
    app.button(key="nav_Analysis").click().run()
    assert not app.exception
    assert app.error[0].value == "Synthetic load failure"
    assert app.session_state["_loaded_route"] == "Overview"
    # st.stop can interrupt cleanup deltas. Browser checks cover the CSS
    # fallback that hides any remaining overlay when the script is no longer running.
    app.checkbox(key="test_failure").uncheck().run()
    assert not app.exception and not app.error
    assert app.session_state["_loaded_route"] == "Analysis"


def test_analysis_tab_loader_does_not_reappear_when_only_the_period_changes(sample_input):
    app = AppTest.from_string("""
from contextlib import contextmanager
from unittest.mock import patch
import pandas as pd
import streamlit as st
from ui.analysis_view import AnalysisView
from ui.loading_view import loading_screen
@contextmanager
def tracked(title, detail, *, enabled):
    st.session_state.setdefault('loading_events', []).append((title, enabled))
    with loading_screen(title, detail, enabled=enabled) as screen:
        yield screen
with patch('ui.analysis_view.loading_screen', tracked), patch.object(AnalysisView, '_render_topic'):
    AnalysisView(st.session_state['input'], pd.DataFrame(), manager=object()).render()
""")
    app.session_state["input"] = sample_input
    app.run()
    assert not app.exception
    assert app.session_state["loading_events"][-1] == ("Loading Progress", True)
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert app.session_state["loading_events"][-1] == ("Loading Progress", False)
    app.session_state["analysis_tab"] = "Exercises"
    app.run()
    assert not app.exception
    assert app.session_state["loading_events"][-1] == ("Loading Exercises", True)
    assert app.session_state["_loaded_analysis_topic"] == "Exercises"
