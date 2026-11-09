"""Version boundaries, session assignment integrity and real calendar reruns."""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import Column, Date, Float, Integer, MetaData, String, Table, Time, create_engine, event, select
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from db.migrate import migrate
from db.plan_schedule import (
    assign_scheduled_session, links, load_plan_session_links, load_scheduled_workouts,
    unassign_scheduled_session,
)
from db.training_plans import save_training_plan
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft


@pytest.fixture
def schedule_data():
    engine = create_engine("sqlite://", future=True, poolclass=StaticPool,
                           connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = MetaData()
    catalog = Table("exercises", metadata, Column("exercise_id", Integer, primary_key=True), Column("exercise_name", String))
    sessions = Table("workout_sessions", metadata,
        Column("session_id", Integer, primary_key=True), Column("session_date", Date),
        Column("start_time", Time), Column("end_time", Time),
        Column("notes", String),
    )
    Table("workout_exercises", metadata,
        Column("workout_exercise_id", Integer, primary_key=True),
        Column("session_id", Integer), Column("exercise_id", Integer),
    )
    Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True), Column("workout_exercise_id", Integer),
        Column("set_number", Integer), Column("repetitions", Integer), Column("weight", Float),
        Column("rir", Integer), Column("duration_seconds", Integer),
    )
    start = date.today() - timedelta(days=date.today().weekday() + 28)
    next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(catalog.insert().values(exercise_id=1, exercise_name="Bench Press"))
        connection.execute(sessions.insert(), [
            {"session_id": 1, "session_date": next_month},
            {"session_id": 2, "session_date": start + timedelta(days=1)},
            {"session_id": 3, "session_date": start + timedelta(days=7)},
        ])
    migrate(engine, apply=True)
    draft = TrainingPlanDraft("Upper", start, (
        TrainingDay("Upper A", 0, (PlannedExercise(1, 3, 6, 10),)),
    ))
    plan = save_training_plan(engine, draft)
    yield engine, start, plan, sessions
    engine.dispose()


def test_schedule_respects_effective_dates_and_midweek_version_change(schedule_data):
    engine, start, plan, _ = schedule_data
    boundary = date.today() + timedelta(days=1)
    new = save_training_plan(engine, replace(plan.draft, effective_from=boundary, days=(
        TrainingDay("Upper B", 2, (PlannedExercise(1, 4, 8, 12),)),
    )), plan_id=plan.plan_id)
    slots = load_scheduled_workouts(engine, plan.plan_id, start - timedelta(days=7), boundary + timedelta(days=14))
    assert slots
    assert all(slot.scheduled_date >= start for slot in slots)
    assert all(slot.scheduled_date < boundary and slot.scheduled_date.weekday() == 0
               for slot in slots if slot.version_id == plan.version_id)
    assert all(slot.scheduled_date >= boundary and slot.scheduled_date.weekday() == 2
               for slot in slots if slot.version_id == new.version_id)
    assert any(slot.version_id == new.version_id for slot in slots)
    old_day = next(slot.day_id for slot in slots if slot.version_id == plan.version_id)
    invalid = boundary + timedelta(days=(0 - boundary.weekday()) % 7)
    with pytest.raises(ValueError, match="not scheduled"):
        assign_scheduled_session(engine, old_day, invalid, 1)


def test_moved_session_can_be_linked_and_unlinked_without_changing_history(schedule_data):
    engine, start, plan, sessions = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    assign_scheduled_session(engine, slot.day_id, start, 1)  # Idempotent retry.
    assigned = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assert assigned.session_id == 1
    assert assigned.performed_on != assigned.scheduled_date
    assert load_plan_session_links(engine) == {1: (slot.day_id, start)}
    unassign_scheduled_session(engine, slot.day_id, start, 2)  # Stale selection cannot unlink another session.
    assert load_plan_session_links(engine)
    unassign_scheduled_session(engine, slot.day_id, start, 1)
    assert load_plan_session_links(engine) == {}
    with engine.connect() as connection:
        assert len(connection.execute(select(sessions)).all()) == 3


def test_session_and_slot_cannot_be_counted_twice_even_across_plans(schedule_data):
    engine, start, plan, _ = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    with pytest.raises(ValueError, match="already linked"):
        assign_scheduled_session(engine, slot.day_id, start + timedelta(days=7), 1)
    with pytest.raises(ValueError, match="already linked"):
        assign_scheduled_session(engine, slot.day_id, start, 2)
    other = save_training_plan(engine, replace(plan.draft, name="Another plan"))
    other_slot = load_scheduled_workouts(engine, other.plan_id, start, start)[0]
    with pytest.raises(ValueError, match="already linked"):
        assign_scheduled_session(engine, other_slot.day_id, start, 1)
    assert len(load_plan_session_links(engine)) == 1


def test_invalid_slot_and_missing_session_are_rejected(schedule_data):
    engine, start, plan, _ = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    for day in (start - timedelta(days=7), start + timedelta(days=1)):
        with pytest.raises(ValueError, match="not scheduled"):
            assign_scheduled_session(engine, slot.day_id, day, 1)
    with pytest.raises(ValueError, match="session not found"):
        assign_scheduled_session(engine, slot.day_id, start, 999)
    assert load_plan_session_links(engine) == {}


def test_deleting_recorded_session_removes_link_and_restores_unlinked_slot(schedule_data):
    engine, start, plan, sessions = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    with engine.begin() as connection:
        connection.execute(sessions.delete().where(sessions.c.session_id == 1))
    assert load_plan_session_links(engine) == {}
    assert load_scheduled_workouts(engine, plan.plan_id, start, start)[0].session_id is None


def test_multiple_workouts_on_same_weekday_keep_separate_slots(schedule_data):
    engine, start, plan, _ = schedule_data
    other = save_training_plan(engine, replace(plan.draft, days=(
        *plan.draft.days, TrainingDay("Upper evening", 0, (PlannedExercise(1, 2, 10, 12),)),
    )))
    slots = load_scheduled_workouts(engine, other.plan_id, start, start)
    assert len(slots) == 2
    assert slots[0].day_id != slots[1].day_id
    assign_scheduled_session(engine, slots[0].day_id, start, 1)
    assign_scheduled_session(engine, slots[1].day_id, start, 2)
    assert {slot.session_id for slot in load_scheduled_workouts(engine, other.plan_id, start, start)} == {1, 2}


def test_revision_cannot_hide_already_linked_future_workouts(schedule_data):
    engine, _, plan, _ = schedule_data
    future = date.today() + timedelta(days=14)
    slot = load_scheduled_workouts(engine, plan.plan_id, future, future + timedelta(days=7))[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 1)
    revision = replace(plan.draft, effective_from=date.today() + timedelta(days=1))
    with pytest.raises(ValueError, match="already linked workout"):
        save_training_plan(engine, revision, plan_id=plan.plan_id)
    assert load_plan_session_links(engine) == {1: (slot.day_id, slot.scheduled_date)}
    unassign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 1)
    assert save_training_plan(engine, revision, plan_id=plan.plan_id).version_number == 2


APP = '''
import pandas as pd
import streamlit as st
from data_manager import DataManager
from ui.history_view import HistoryView
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
frame = manager.load_sessions()
frame["exercise_name"] = "Bench Press"
frame["repetitions"] = 8
frame["weight"] = 60.
frame["set_number"] = 1
if st.session_state.get("empty_history"):
    frame = frame.iloc[:0]
month = st.session_state["test_month"]
if month:
    frame = frame.loc[frame.session_date.dt.strftime("%Y-%m") == month]
HistoryView({}, frame, month, data_manager=manager, exercise_names={1: "Bench Press"}).render()
'''


def test_calendar_links_session_from_another_month_and_removes_link(schedule_data):
    engine, start, plan, _ = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["test_month"] = f"{start:%Y-%m}"
    app.run()
    assert not app.exception
    assert app.selectbox(key="adherence_plan").value == plan.plan_id
    app.button(key=f"history_date_{start}").click().run()
    assert "1 planned" in app.button(key=f"history_date_{start}").help
    prefix = f"schedule_{slot.day_id}_{start}"
    with engine.connect() as connection:
        recorded_date = connection.execute(select(schedule_data[3].c.session_date).where(schedule_data[3].c.session_id == 1)).scalar_one()
    app.selectbox(key=f"{prefix}_date").select(recorded_date).run()
    app.selectbox(key=f"{prefix}_session").select(1).run()
    app.selectbox(key=f"{prefix}_date").select(start + timedelta(days=1)).run()
    assert app.selectbox(key=f"{prefix}_session").value is None
    assert app.button(key=f"{prefix}_link").disabled
    app.selectbox(key=f"{prefix}_date").select(recorded_date).run()
    app.selectbox(key=f"{prefix}_session").select(1).run()
    app.button(key=f"{prefix}_link").click().run()
    assert not app.exception
    assert not app.error
    assert "1 linked" in app.button(key=f"history_date_{start}").help
    assert any("different day" in message.value for message in app.success)
    assert not app.dataframe
    assert not app.get("plotly_chart")
    app.button(key=f"{prefix}_unlink").click().run()
    assert not app.exception
    assert load_plan_session_links(engine) == {}


def test_plan_calendar_is_available_without_history_and_browses_future_months(schedule_data):
    engine, _, _, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(sessions.delete())
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["test_month"] = None
    app.session_state["empty_history"] = True
    app.run()
    assert not app.exception
    future = date.today() + timedelta(days=60)
    app.selectbox(key="history_month").select(f"{future:%Y-%m}").run()
    assert not app.exception
    assert any("planned" in button.help for button in app.button if button.key.startswith("history_date_"))
    assert load_plan_session_links(engine) == {}
