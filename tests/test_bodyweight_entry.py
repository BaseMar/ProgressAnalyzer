"""Manual, imported and corrected bodyweight logs through real UI reruns."""
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import Column, Date, Float, MetaData, Table, event, select
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from db.plan_adherence import actual_exercises, actual_sets
from db.set_loads import loads
from mapper import map_workout_set
from models.set_load import SetLoad
from ui.history_view import _set_pills
from test_plan_schedule import schedule_data


@pytest.fixture
def entry_data(schedule_data):
    engine = schedule_data[0]
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE exercises ADD COLUMN body_part VARCHAR")
        connection.exec_driver_sql("ALTER TABLE exercises ADD COLUMN category VARCHAR")
        connection.exec_driver_sql("INSERT INTO exercises (exercise_id, exercise_name) VALUES (2, 'Dead hang'), (3, 'Pull-up'), (4, 'Assisted dips')")
        connection.exec_driver_sql("CREATE TABLE body_composition (measurement_date DATETIME, weight FLOAT)")
        connection.exec_driver_sql("INSERT INTO body_composition VALUES ('2026-01-01 08:00:00', 75), ('2026-02-01 20:00:00', 80), ('2026-03-01 08:00:00', 90)")
    manager = object.__new__(DataManager)
    manager.engine = engine
    return manager


def timed_set(weight=0, body=80):
    return {"reps": 0, "duration_seconds": 40, "weight": weight, "rir": None,
            "load": SetLoad("bodyweight", weight, body), "is_warmup": False}


def test_mass_suggestion_never_uses_future_measurements(entry_data):
    assert entry_data.suggest_body_mass(date(2025, 12, 31)) is None
    assert entry_data.suggest_body_mass(date(2026, 1, 15)) == {"date": date(2026, 1, 1), "weight": 75.0}
    assert entry_data.suggest_body_mass(date(2026, 2, 1)) == {"date": date(2026, 2, 1), "weight": 80.0}
    assert entry_data.suggest_body_mass(date(2026, 2, 15))["weight"] == 80.0
    with entry_data.engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO body_composition VALUES ('2026-02-10', NULL), ('2026-02-11', 0), ('2026-02-12', -1)")
    assert entry_data.suggest_body_mass(date(2026, 2, 15))["weight"] == 80.0


def test_missing_measurement_table_is_supported(schedule_data):
    manager = object.__new__(DataManager)
    manager.engine = schedule_data[0]
    assert manager.suggest_body_mass(date.today()) is None


def test_mass_suggestion_accepts_native_date_values(entry_data, monkeypatch):
    table = Table("body_composition", MetaData(), Column("measurement_date", Date), Column("weight", Float))
    monkeypatch.setattr("db.set_loads.measurements", table)
    with entry_data.engine.begin() as connection:
        connection.execute(table.delete())
        connection.execute(table.insert().values(measurement_date=date(2026, 2, 1), weight=80))
    assert entry_data.suggest_body_mass(date(2026, 2, 15)) == {"date": date(2026, 2, 1), "weight": 80}


def test_mass_suggestion_handles_legacy_text_and_malformed_dates(entry_data):
    with entry_data.engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE body_composition")
        connection.exec_driver_sql("CREATE TABLE body_composition (measurement_date TEXT, weight FLOAT)")
        connection.exec_driver_sql("""INSERT INTO body_composition VALUES
            ('2026-02-01', 75), ('2026-02-12T08:00:00', 77),
            ('2026-02-12T20:00:00', 79), ('2026-02-20', 90),
            ('bad-date', 100), (NULL, 100)""")
    assert entry_data.suggest_body_mass(date(2026, 2, 15)) == {"date": date(2026, 2, 12), "weight": 79}
    assert entry_data.suggest_body_mass(date(2025, 12, 31)) is None


def test_batch_and_manual_append_share_session_and_preserve_snapshots(entry_data):
    day = date(2026, 2, 15)
    entry_data.add_workout_session(day, "Imported", [
        {"name": "Dead hang", "sets": [timed_set(5)]},
        {"name": "Pull-up", "sets": [{"reps": 8, "weight": 10, "rir": 2, "load": SetLoad("bodyweight", 10, 80)}]},
    ])
    entry_data.add_full_session(day, "Manual", "Dead hang", [timed_set(0)], None, None)
    frame = entry_data.load_sets_ui().loc[lambda rows: pd.to_datetime(rows.session_date).dt.date == day]
    assert frame.session_id.nunique() == 1
    assert len(frame) == 3
    assert frame.body_mass_kg.tolist() == [80, 80, 80]
    assert sorted(frame.weight) == [0, 5, 10]
    with entry_data.engine.begin() as connection:
        connection.exec_driver_sql("UPDATE body_composition SET weight=100")
    assert entry_data.load_sets_raw().body_mass_kg.eq(80).all()


def test_batch_failure_rolls_back_exercises_loads_and_session(entry_data):
    day = date(2026, 2, 15)
    with pytest.raises(ValueError, match="Exercise not found"):
        entry_data.add_workout_session(day, "Imported", [
            {"name": "Dead hang", "sets": [timed_set(5)]},
            {"name": "Missing exercise", "sets": [timed_set()]},
        ])
    assert not entry_data.load_sessions().session_date.dt.date.eq(day).any()
    with entry_data.engine.connect() as connection:
        assert connection.execute(select(actual_exercises)).all() == []
        assert connection.execute(select(loads)).all() == []


def test_database_load_write_failure_rolls_back_batch(entry_data):
    def fail(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO workout_set_loads"):
            raise RuntimeError("Load write failed")

    event.listen(entry_data.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Load write failed"):
            entry_data.add_full_session(date(2026, 2, 15), "Manual", "Dead hang", [timed_set()], None, None)
    finally:
        event.remove(entry_data.engine, "before_cursor_execute", fail)
    with entry_data.engine.connect() as connection:
        assert connection.execute(select(actual_exercises)).all() == []
        assert connection.execute(select(actual_sets)).all() == []


def test_explicit_load_rejected_before_insert_when_setup_missing(entry_data):
    with entry_data.engine.begin() as connection:
        loads.drop(connection)
    with pytest.raises(ValueError, match="setup"):
        entry_data.add_full_session(date(2026, 2, 15), "Manual", "Dead hang", [timed_set()], None, None)
    legacy = {"reps": 8, "weight": 60, "rir": 2}
    assert entry_data.add_full_session(date(2026, 2, 15), "Imported", "Bench Press", [legacy], None, None)


ENTRY_APP = '''
import streamlit as st
from data_manager import DataManager
from ui.workout_entry_view import render_workout_entry
manager = object.__new__(DataManager)
manager.engine = st.session_state["engine"]
if st.session_state.get("history_add_workout", True):
    render_workout_entry(manager)
else:
    st.success(st.session_state.get("history_workout_notice", "Saved"))
    st.dataframe(manager.load_sets_ui())
'''


def start_entry(manager, source=ENTRY_APP):
    app = AppTest.from_string(source, default_timeout=30)
    app.session_state["engine"] = manager.engine
    app.run()
    assert not app.exception and not app.error
    return app


def open_hang(app):
    app.date_input(key="entry_date").set_value(date(2026, 2, 15)).run()
    app.selectbox(key="entry_exercise").select(2).run()
    assert app.radio(key="entry_2_measure").value == "Seconds"
    assert app.selectbox(key="entry_2_kind").value == "bodyweight"
    return app


def test_manual_dead_hang_suggests_mass_and_saves_per_set_added_weight(entry_data):
    app = open_hang(start_entry(entry_data))
    mass = app.number_input(key="entry_2_2026-02-15_bodyweight_body")
    assert mass.value == 80.0
    assert any("2026-02-01" in item.value for item in app.caption)
    mass.set_value(82.0)
    app.session_state["entry_2_Seconds_3_sets"] = {"edited_rows": {0: {"kg": 5.0, "Seconds": 45}}, "added_rows": [], "deleted_rows": []}
    app.button(key="entry_save").click().run()
    assert not app.exception and not app.error
    rows = [map_workout_set(row) for row in entry_data.load_sets_raw().to_dict("records")]
    assert app.session_state["history_month"] == "2026-02"
    assert app.session_state["history_day_2026-02"] == date(2026, 2, 15)
    assert [row.duration_seconds for row in rows] == [45, 30, 30]
    assert [row.load.total_load_kg for row in rows] == [87, 82, 82]
    assert all(row.repetitions == 0 for row in rows)


def test_manual_date_change_refreshes_mass_and_missing_mass_stays_unknown(entry_data):
    app = open_hang(start_entry(entry_data))
    app.date_input(key="entry_date").set_value(date(2026, 1, 15)).run()
    assert app.number_input(key="entry_2_2026-01-15_bodyweight_body").value == 75.0
    app.date_input(key="entry_date").set_value(date(2025, 12, 1)).run()
    assert app.number_input(key="entry_2_2025-12-01_bodyweight_body").value is None
    app.button(key="entry_save").click().run()
    assert not app.exception and not app.error
    row = map_workout_set(entry_data.load_sets_raw().iloc[0].to_dict())
    assert row.load.total_load_kg is None


@pytest.mark.parametrize("assistance", [None, 20.0])
def test_assisted_entry_saves_unknown_or_measured_support(entry_data, assistance):
    app = start_entry(entry_data)
    app.date_input(key="entry_date").set_value(date(2026, 2, 15)).run()
    app.selectbox(key="entry_exercise").select(4).run()
    assert app.selectbox(key="entry_4_kind").value == "assisted_bodyweight"
    assert app.number_input(key="entry_4_assistance").value is None
    if assistance is not None:
        app.number_input(key="entry_4_assistance").set_value(assistance).run()
        assert any("60 kg" in item.value for item in app.caption)
    app.button(key="entry_save").click().run()
    assert not app.exception and not app.error
    row = map_workout_set(entry_data.load_sets_raw().iloc[0].to_dict())
    assert row.load.assistance_kg == assistance
    assert row.load.total_load_kg == (60 if assistance is not None else None)


def test_invalid_assistance_keeps_form_and_database_unchanged(entry_data):
    app = start_entry(entry_data)
    app.date_input(key="entry_date").set_value(date(2026, 2, 15)).run()
    app.selectbox(key="entry_exercise").select(4).run()
    app.number_input(key="entry_4_assistance").set_value(100.0).run()
    assert not app.exception
    assert any("exceed" in item.value for item in app.error)
    with entry_data.engine.connect() as connection:
        assert connection.execute(select(actual_sets)).all() == []


def test_manual_selection_keeps_exercise_id_when_catalog_names_repeat(entry_data):
    with entry_data.engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO exercises (exercise_id, exercise_name) VALUES (5, 'Dead hang')")
    app = start_entry(entry_data)
    app.selectbox(key="entry_exercise").select(5).run()
    app.button(key="entry_save").click().run()
    assert not app.exception and not app.error
    with entry_data.engine.connect() as connection:
        assert connection.execute(select(actual_exercises.c.exercise_id)).scalar_one() == 5


CORRECTION_APP = '''
from datetime import date
import streamlit as st
from data_manager import DataManager
from ui.set_load_view import render_set_load_correction
from ui.history_view import _set_pills
manager = object.__new__(DataManager)
manager.engine = st.session_state["engine"]
frame = manager.load_sets_ui()
sid = int(frame.iloc[0].session_id)
st.markdown(_set_pills(frame), unsafe_allow_html=True)
render_set_load_correction(manager, session_id=sid, workout_date=date(2026, 2, 15))
'''


def test_history_correction_keeps_legacy_until_explicitly_changed(entry_data):
    entry_data.add_full_session(date(2026, 2, 15), "Legacy", "Dead hang", [
        {"reps": 40, "duration_seconds": 40, "weight": 0, "rir": None}], None, None)
    app = start_entry(entry_data, CORRECTION_APP)
    assert not app.selectbox
    frame = entry_data.load_sets_ui()
    sid, set_id = int(frame.iloc[0].session_id), int(frame.iloc[0].set_id)
    app.toggle(key=f"edit_load_{sid}").set_value(True).run()
    key = f"load_{sid}_{set_id}"
    assert app.selectbox(key=f"{key}_kind").value == "legacy"
    app.selectbox(key=f"{key}_kind").select("bodyweight").run()
    assert app.number_input(key=f"{key}_2026-02-15_bodyweight_body").value == 80
    app.number_input(key=f"{key}_weight").set_value(5.0)
    app.button(key=f"{key}_save").click().run()
    assert not app.exception and not app.error
    assert any("85 kg total" in item.value for item in app.markdown)
    row = map_workout_set(entry_data.load_sets_raw().iloc[0].to_dict())
    assert row.load == SetLoad("bodyweight", 5, 80)


IMPORT_APP = '''
from datetime import date
import streamlit as st
from data_manager import DataManager
from ui.sidebar_upload import SidebarUpload
manager = object.__new__(DataManager)
manager.engine = st.session_state["engine"]
upload = SidebarUpload(manager=manager)
parsed = upload._parse_txt("1. Dead hang\\nWorking: 40s / 30s\\n2. Bench Press\\n8x60\\nRIR: 2")
reviewed = upload._review_loads(parsed, date(2026, 2, 15), "test")
st.session_state["reviewed"] = reviewed
if st.button("Save import", key="import_save"):
    st.session_state["exercise_mapping"] = {}
    upload._process(reviewed, date(2026, 2, 15), None, None)
'''


def test_import_preserves_original_by_default_and_can_add_body_mass(entry_data):
    app = start_entry(entry_data, IMPORT_APP)
    assert app.selectbox(key="import_test_0_kind").value == "legacy"
    assert all("load" not in item for ex in app.session_state["reviewed"] for item in ex["sets"])
    app.selectbox(key="import_test_0_kind").select("bodyweight").run()
    app.session_state["import_test_0_weights"] = {"edited_rows": {0: {"kg": 5.0}}, "added_rows": [], "deleted_rows": []}
    app.button(key="import_save").click().run()
    assert not app.exception and not app.error
    rows = entry_data.load_sets_ui()
    assert app.session_state["history_day_2026-02"] == date(2026, 2, 15)
    assert rows.session_id.nunique() == 1
    hang = rows.loc[rows.exercise_name == "Dead hang"]
    assert [map_workout_set(row).load.total_load_kg for row in hang.to_dict("records")] == [85, 80]
    assert rows.loc[rows.exercise_name == "Bench Press", "load_type"].isna().all()


def test_history_badges_show_time_body_added_weight_and_support():
    frame = pd.DataFrame([{"workout_exercise_id": 1, "set_number": 1, "repetitions": 0,
        "duration_seconds": 40, "weight": 5, "rir": None, "load_type": "bodyweight", "body_mass_kg": 80, "assistance_kg": 0}])
    html = _set_pills(frame)
    assert "40s" in html and "body 80 kg + 5 kg" in html and "85 kg total" in html
    frame.loc[0, ["load_type", "weight", "assistance_kg"]] = ["assisted_bodyweight", 0, 20]
    html = _set_pills(frame)
    assert "20 kg assistance" in html and "60 kg total" in html
    frame.loc[0, "assistance_kg"] = None
    assert "total unknown" in _set_pills(frame)


def test_manual_entry_is_reachable_and_returns_to_saved_day_in_history(entry_data):
    app = start_entry(entry_data, '''
import streamlit as st
from data_manager import DataManager
from ui.history_view import HistoryView
manager = object.__new__(DataManager)
manager.engine = st.session_state["engine"]
HistoryView({}, manager.load_sets_ui(), data_manager=manager).render()
''')
    app.button(key="history_add_workout_button").click().run()
    assert len(app.get("file_uploader")) == 1
    app.radio(key="workout_entry_mode").set_value("Enter exercise").run()
    assert not app.get("file_uploader")
    open_hang(app)
    app.button(key="entry_save").click().run()
    assert not app.exception and not app.error
    assert not app.get("data_editor")
    assert app.selectbox(key="history_month").value == "2026-02"
    assert any("Sessions on 15 Feb 2026" in item.value for item in app.markdown)
    assert any("80 kg total" in item.value for item in app.markdown)
    assert any("Saved Dead hang" in item.value for item in app.success)
