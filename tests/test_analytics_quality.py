"""Regression coverage for honest units, dated charts and explicit warm-up labels."""
from dataclasses import replace
from datetime import date, time
import json
import pandas as pd

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from test_plan_schedule import schedule_data
from data_manager import DataManager
from db.plan_adherence import load_plan_adherence
from db.plan_schedule import assign_scheduled_session
from db.set_classifications import classifications, save_set_classifications
from mapper import map_workout_set
from metrics.fatigue_metrics import compute_fatigue_metrics
from metrics.metrics_engine import compute_all_metrics
from metrics.plan_adherence import compute_plan_adherence
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet
from ui.sidebar_upload import SidebarUpload


def test_explicit_warmup_is_excluded_from_all_metric_groups(sample_input):
    labelled = replace(sample_input, sets=[replace(sample_input.sets[0], is_warmup=True), *sample_input.sets[1:]])
    expected = replace(sample_input, sets=sample_input.sets[1:])
    assert compute_all_metrics(labelled) == compute_all_metrics(expected)
    unknown = replace(sample_input, sets=[replace(item, is_warmup=None) for item in sample_input.sets])
    working = replace(sample_input, sets=[replace(item, is_warmup=False) for item in sample_input.sets])
    assert compute_all_metrics(unknown) == compute_all_metrics(working)


def test_fatigue_has_dates_and_consecutive_sessions_follow_chronology(sample_input):
    sessions = [WorkoutSession(sid, date(2026, 5, sid), time(8), None) for sid in (1, 3, 4, 2)]
    data = replace(sample_input, sessions=sessions,
        workout_exercises=[WorkoutExercise(sid * 100, sid, 1) for sid in (1, 2, 3, 4)],
        sets=[WorkoutSet(sid * 100, 1, 10, 10. if sid == 2 else 1000., 3 if sid == 2 else 0) for sid in (1, 2, 3, 4)])
    fatigue = compute_fatigue_metrics(data)
    assert list(fatigue["per_session"]) == [1, 2, 3, 4]
    assert fatigue["global"]["max_consecutive_high_fatigue_sessions"] == 2
    assert fatigue["per_session"][3]["session_date"] == date(2026, 5, 3)


def test_fatigue_ui_displays_kilograms_percentages_and_nonempty_chart(sample_input):
    app = AppTest.from_string('''
import streamlit as st
from ui.analytics_view import AnalyticsView
AnalyticsView(st.session_state["metrics"])._fatigue_section()
''', default_timeout=30)
    app.session_state["metrics"] = compute_all_metrics(sample_input)
    app.run()
    assert not app.exception
    values = {item.label: item.value for item in app.metric}
    assert values["Mean session e1RM"].endswith(" kg")
    assert values["High-score sessions"].endswith("%")
    charts = app.get("plotly_chart")
    assert len(charts) == 1
    assert len(json.loads(charts[0].proto.spec)["data"][0]["x"]) == 3
    assert not app.success


def test_positive_lowest_change_is_not_called_regression():
    app = AppTest.from_string('''
from ui.analytics_view import AnalyticsView
AnalyticsView({"progress": {"per_exercise": {
    1: {"exercise_name": "Bench", "progress_pct": 10., "exposure_count": 3},
    2: {"exercise_name": "Row", "progress_pct": 5., "exposure_count": 3},
}}})._progress_section()
''', default_timeout=30).run()
    assert not app.exception
    values = {item.label: item.value for item in app.metric}
    assert values["Lowest change"] == "Row"
    assert "Top Regressor" not in values


def test_mapper_keeps_unknown_type_and_missing_rir_unknown():
    row = dict(workout_exercise_id=1, set_number=1, repetitions=8, weight=60., rir=float("nan"), is_warmup=float("nan"))
    mapped = map_workout_set(row)
    assert mapped.is_warmup is None
    assert mapped.rir is None


def test_txt_explicit_warmup_and_working_tokens_preserve_unmarked_unknown():
    upload = object.__new__(SidebarUpload)
    parsed = upload._parse_txt("1. Bench Press\nWarm-up: 10x20 / Working: 8x60 / 8x60\n8x60\n")
    sets = parsed[0]["sets"]
    assert [item.get("is_warmup") for item in sets] == [True, False, False, None]
    inline = upload._parse_txt("1. Bench Press: Warm-up: 10x20 / Working: 8x60\n")
    assert inline[0]["name"] == "Bench Press"
    assert [item["is_warmup"] for item in inline[0]["sets"]] == [True, False]


def imported_session(schedule_data):
    engine, start, plan, _ = schedule_data
    dm = object.__new__(DataManager)
    dm.engine = engine
    dm.add_full_session(start.isoformat(), "Test", "Bench Press", [
        {"reps": 8, "weight": 20., "rir": 3, "is_warmup": True},
        {"reps": 8, "weight": 60., "rir": 2, "is_warmup": False},
        {"reps": 8, "weight": 60., "rir": None},
    ], None, None)
    session_id = int(dm.load_sessions().loc[lambda frame: frame.session_date.dt.date == start, "session_id"].iloc[0])
    data = dm.load_plan_adherence(plan.plan_id, start, start)
    assign_scheduled_session(engine, data.workouts[0].slot.day_id, start, session_id)
    return dm, session_id


def test_imported_labels_roundtrip_and_only_nonwarmups_cover_plan(schedule_data):
    dm, sid = imported_session(schedule_data)
    engine, start, plan, _ = schedule_data
    frame = dm.load_session_sets(sid)
    assert frame.is_warmup.iloc[0] == True
    assert frame.is_warmup.iloc[1] == False
    assert pd.isna(frame.is_warmup.iloc[2])
    data = load_plan_adherence(engine, plan.plan_id, start, start)
    assert compute_plan_adherence(data, as_of=date.today())["summary"]["covered_sets"] == 2
    first_id = int(frame.iloc[0].set_id)
    save_set_classifications(engine, sid, {first_id: None})
    assert compute_plan_adherence(load_plan_adherence(engine, plan.plan_id, start, start), as_of=date.today())["summary"]["covered_sets"] == 3
    with pytest.raises(ValueError, match="selected session"):
        save_set_classifications(engine, sid, {first_id: True, 99999: False})
    with engine.connect() as connection:
        assert connection.execute(select(classifications).where(classifications.c.set_id == first_id)).first() is None


def test_label_editor_updates_storage_and_plan_coverage(schedule_data):
    dm, sid = imported_session(schedule_data)
    app = AppTest.from_string('''
import streamlit as st
from ui.set_classification_view import render_set_classification
render_set_classification(st.session_state["manager"])
''', default_timeout=30)
    app.session_state["manager"] = dm
    app.session_state["classify_session"] = sid
    app.run()
    assert not app.exception
    app.session_state[f"set_types_{sid}"] = {"edited_rows": {0: {"Type": "Working"}}, "added_rows": [], "deleted_rows": []}
    app.button(key=f"save_set_types_{sid}").click().run()
    assert not app.exception
    assert not app.error
    assert dm.load_session_sets(sid).iloc[0].is_warmup == False
