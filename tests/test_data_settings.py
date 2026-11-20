"""Exercise settings open from History and save only the selected exercise."""

from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from db.load_profiles import profiles
from test_bodyweight_entry import entry_data as entry_data
from test_load_profiles import raw_entry
from test_plan_schedule import schedule_data as schedule_data

APP = """
import streamlit as st
from ui.history_view import HistoryView
manager = st.session_state['manager']
HistoryView({}, manager.load_sets_ui(), data_manager=manager).render()
"""


def open_settings(manager):
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["manager"] = manager
    app.run()
    assert not app.exception and not app.error
    assert not any(item.label == "Exercise load settings" for item in app.expander)
    app.button(key="history_data_settings_button").click().run()
    assert not app.exception and not app.error
    return app


def test_opening_settings_shows_current_profile_without_mutating_history(entry_data):
    raw_entry(entry_data, 4, 20)
    before = entry_data.load_sets_raw().to_dict("records")
    app = open_settings(entry_data)
    assert not any(toggle.key == "edit_exercise_conventions" for toggle in app.toggle)
    app.selectbox(key="load_profile_exercise").select(4).run()
    assert "Current settings" in "".join(item.value for item in app.markdown)
    assert app.button_group(key="profile_4_kind").value == "assisted_bodyweight"
    assert entry_data.load_sets_raw().to_dict("records") == before
    with entry_data.engine.connect() as connection:
        assert connection.execute(select(profiles)).all() == []


def test_unresolved_edit_opens_correct_exercise_and_save_resolves_only_its_sets(entry_data):
    raw_entry(entry_data, 4, 20)
    raw_entry(entry_data, 4, 25)
    raw_entry(entry_data, 2, 5)
    app = open_settings(entry_data)
    app.session_state["data_settings_tab"] = "Unresolved sets"
    app.run()
    assert not app.exception and not app.error
    assert "2 exercises · 3 unresolved sets" in "".join(item.value for item in app.markdown)
    assert app.button(key="data_settings_edit_4")
    assert app.button(key="data_settings_edit_2")
    app.button(key="data_settings_edit_4").click().run()
    assert not app.exception and not app.error
    assert app.session_state["data_settings_tab"] == "Exercise settings"
    assert app.selectbox(key="load_profile_exercise").value == 4
    app.selectbox(key="profile_4_assisted_bodyweight_history").select("assistance").run()
    app.button(key="save_exercise_convention").click().run()
    assert not app.exception and not app.error
    assert any("Updated 2 historical sets" in message.value for message in app.success)
    profile = entry_data.load_exercise_load_profiles()[4]
    assert profile.source == "user" and profile.legacy_mode == "assistance"
    rows = entry_data.load_sets_ui()
    changed = rows.loc[rows.exercise_name == "Assisted dips"]
    assert set(changed.assistance_kg) == {20, 25}
    assert set(changed.weight) == {0}
    untouched = rows.loc[rows.exercise_name == "Dead hang"]
    assert untouched.load_type.isna().all()
    assert list(untouched.weight) == [5]
    app.session_state["data_settings_tab"] = "Unresolved sets"
    app.run()
    assert not app.exception and not app.error
    assert not any(button.key == "data_settings_edit_4" for button in app.button)
    assert app.button(key="data_settings_edit_2")


def test_changing_exercise_type_resets_incompatible_kilogram_modes(entry_data):
    old = entry_data.load_exercise_load_profiles()[4]
    entry_data.save_exercise_load_profile(replace(old, legacy_mode="assistance", source="user"))
    app = open_settings(entry_data)
    app.selectbox(key="load_profile_exercise").select(4).run()
    app.button_group(key="profile_4_kind").set_value("bodyweight").run()
    assert not app.exception and not app.error
    assert app.selectbox(key="profile_4_bodyweight_input").value == "additional"
    assert app.selectbox(key="profile_4_bodyweight_history").value == "unknown"
    app.button(key="save_exercise_convention").click().run()
    assert not app.exception and not app.error
    saved = entry_data.load_exercise_load_profiles()[4]
    assert (saved.load_type, saved.input_mode, saved.legacy_mode) == (
        "bodyweight",
        "additional",
        "unknown",
    )


def test_empty_unresolved_tab_does_not_normalize_convertible_records(entry_data):
    raw_entry(entry_data, 1, 60)
    app = open_settings(entry_data)
    app.session_state["data_settings_tab"] = "Unresolved sets"
    app.run()
    assert not app.exception and not app.error
    assert any(item.value == "No unresolved sets." for item in app.success)
    assert entry_data.load_sets_ui().load_type.isna().all()


def test_failed_save_retains_input_and_allows_retry(entry_data, monkeypatch):
    raw_entry(entry_data, 4, 20)
    app = open_settings(entry_data)
    app.selectbox(key="load_profile_exercise").select(4).run()
    app.selectbox(key="profile_4_assisted_bodyweight_history").select("assistance").run()
    original = DataManager.normalize_load_history

    def fail(*args, **kwargs):
        raise OperationalError("save", {}, RuntimeError("unavailable"))

    monkeypatch.setattr(DataManager, "normalize_load_history", fail)
    app.button(key="save_exercise_convention").click().run()
    assert not app.exception
    assert "could not be loaded or saved" in app.error[0].value
    assert app.selectbox(key="profile_4_assisted_bodyweight_history").value == "assistance"
    assert entry_data.load_sets_ui().load_type.isna().all()
    monkeypatch.setattr(DataManager, "normalize_load_history", original)
    app.button(key="save_exercise_convention").click().run()
    assert not app.exception and not app.error
    assert entry_data.load_sets_ui().load_type.tolist() == ["assisted_bodyweight"]


def test_missing_setup_and_empty_catalog_have_readable_states(entry_data, monkeypatch):
    monkeypatch.setattr(DataManager, "exercise_load_profile_storage_ready", lambda *args: False)
    app = open_settings(entry_data)
    assert any("Complete database setup" in item.value for item in app.info)
    monkeypatch.setattr(DataManager, "exercise_load_profile_storage_ready", lambda *args: True)
    monkeypatch.setattr(DataManager, "load_exercise_load_profiles", lambda *args: {})
    app.run()
    assert not app.exception and not app.error
    assert any(item.value == "No exercises yet." for item in app.info)


def test_duplicate_exercise_names_are_distinguishable(entry_data):
    with entry_data.engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO exercises (exercise_id, exercise_name) VALUES (5, 'Dead hang')"
        )
    app = open_settings(entry_data)
    assert "Dead hang · #2" in app.selectbox(key="load_profile_exercise").options
    assert "Dead hang · #5" in app.selectbox(key="load_profile_exercise").options
