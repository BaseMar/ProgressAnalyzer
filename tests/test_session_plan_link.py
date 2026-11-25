"""Session header actions edit one plan assignment through a real dialog."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from db.plan_adherence import actual_exercises, matches
from db.plan_schedule import (
    assign_scheduled_session,
    load_plan_session_links,
    load_scheduled_workouts,
    load_session_plan_assignments,
)
from db.training_plans import days, exercises, save_training_plan
from test_plan_schedule import APP
from test_plan_schedule import schedule_data as schedule_data


def start_app(data):
    engine, _, _, sessions = data
    with engine.connect() as connection:
        recorded_date = connection.execute(
            select(sessions.c.session_date).where(sessions.c.session_id == 1)
        ).scalar_one()
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["test_month"] = f"{recorded_date:%Y-%m}"
    app.session_state[f"history_day_{recorded_date:%Y-%m}"] = recorded_date
    app.run()
    assert not app.exception and not app.error
    return app


def test_header_dialog_links_changes_and_removes_a_moved_session(schedule_data):
    engine, start, plan, _ = schedule_data
    app = start_app(schedule_data)
    assert not any(item.label == "Plan assignments" for item in app.expander)
    assert app.button(key="history_session_link_1").label == "Link to plan"
    app.button(key="history_session_link_1").click().run()
    assert not app.exception
    app.date_input(key="history_link_1_week").set_value(start).run()
    app.button(key="history_link_1_save").click().run()
    assert not app.exception and not app.error
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assert load_plan_session_links(engine) == {1: (slot.day_id, start)}
    assert app.button(key="history_session_link_1").label == "Edit plan link"
    assert any("sets · Upper A" in item.value for item in app.markdown)
    assert app.success[0].value == "Session linked to Upper A."
    app.toggle(key="calendar_plan_overlay").set_value(False).run()
    assert app.button(key="history_session_link_1").label == "Edit plan link"
    app.button(key="history_session_link_1").click().run()
    app.date_input(key="history_link_1_week").set_value(start + timedelta(days=7)).run()
    app.button(key="history_link_1_save").click().run()
    assert not app.exception and not app.error
    assert load_plan_session_links(engine) == {1: (slot.day_id, start + timedelta(days=7))}
    app.button(key="history_session_link_1").click().run()
    app.button(key="history_link_1_unlink").click().run()
    assert not app.exception and not app.error
    assert load_plan_session_links(engine) == {}
    assert app.button(key="history_session_link_1").label == "Link to plan"


def test_header_resolves_linked_plan_even_when_another_plan_is_selected(schedule_data):
    engine, start, plan, _ = schedule_data
    other = save_training_plan(engine, replace(plan.draft, name="Another plan"))
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    app = start_app(schedule_data)
    app.selectbox(key="adherence_plan").select(other.plan_id).run()
    assert app.button(key="history_session_link_1").label == "Edit plan link"
    app.button(key="history_session_link_1").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="history_link_1_plan").value == plan.plan_id
    app.selectbox(key="history_link_1_plan").select(other.plan_id).run()
    app.button(key="history_link_1_save").click().run()
    assert not app.exception and not app.error
    assignment = load_session_plan_assignments(engine, (1,))[1]
    assert assignment["plan_id"] == other.plan_id
    assert assignment["plan_name"] == "Another plan"


def test_dialog_excludes_occupied_slots_and_handles_weeks_before_plan_start(schedule_data):
    engine, start, plan, _ = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 2)
    app = start_app(schedule_data)
    app.button(key="history_session_link_1").click().run()
    for week in (start, start - timedelta(days=7)):
        app.date_input(key="history_link_1_week").set_value(week).run()
        assert not app.exception and not app.error
        assert any("No available workouts" in info.value for info in app.info)
        assert not any(button.key == "history_link_1_save" for button in app.button)
    assert load_plan_session_links(engine) == {2: (slot.day_id, start)}


def test_dialog_save_failure_retains_existing_assignment_and_allows_retry(
    schedule_data, monkeypatch
):
    engine, start, plan, _ = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    original = DataManager.assign_scheduled_session

    def fail(*args, **kwargs):
        raise OperationalError("save", {}, RuntimeError("unavailable"))

    app = start_app(schedule_data)
    app.button(key="history_session_link_1").click().run()
    app.date_input(key="history_link_1_week").set_value(start + timedelta(days=7)).run()
    monkeypatch.setattr(DataManager, "assign_scheduled_session", fail)
    app.button(key="history_link_1_save").click().run()
    assert not app.exception
    assert "could not be loaded or saved" in app.error[0].value
    assert load_plan_session_links(engine) == {1: (slot.day_id, start)}
    monkeypatch.setattr(DataManager, "assign_scheduled_session", original)
    app.button(key="history_link_1_save").click().run()
    assert not app.exception and not app.error
    assert load_plan_session_links(engine) == {1: (slot.day_id, start + timedelta(days=7))}


def test_replacement_rolls_back_old_link_and_confirmations_when_target_is_occupied(schedule_data):
    engine, start, plan, sessions = schedule_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    assign_scheduled_session(engine, slot.day_id, start + timedelta(days=7), 2)
    with engine.begin() as connection:
        target_id = connection.execute(
            select(exercises.c.plan_exercise_id)
            .join(days)
            .where(days.c.version_id == plan.version_id)
        ).scalar_one()
        connection.execute(
            actual_exercises.insert().values(workout_exercise_id=100, session_id=1, exercise_id=1)
        )
        connection.execute(
            matches.insert().values(
                session_id=1, plan_exercise_id=target_id, workout_exercise_id=100
            )
        )
    before = load_plan_session_links(engine)
    with pytest.raises(ValueError, match="already linked"):
        assign_scheduled_session(
            engine, slot.day_id, start + timedelta(days=7), 1, replace_existing=True
        )
    assert load_plan_session_links(engine) == before
    assign_scheduled_session(engine, slot.day_id, start, 1, replace_existing=True)
    with engine.connect() as connection:
        assert len(connection.execute(select(matches)).all()) == 1
    assign_scheduled_session(
        engine, slot.day_id, start + timedelta(days=14), 1, replace_existing=True
    )
    assert load_plan_session_links(engine)[1] == (slot.day_id, start + timedelta(days=14))
    with engine.connect() as connection:
        assert connection.execute(select(matches)).all() == []
        assert len(connection.execute(select(sessions)).all()) == 3


def test_multiple_linked_sessions_keep_separate_header_actions_and_replacement_controls(
    schedule_data,
):
    engine, start, plan, sessions = schedule_data
    other = save_training_plan(engine, replace(plan.draft, name="Other plan"))
    with engine.begin() as connection:
        recorded_date = connection.execute(
            select(sessions.c.session_date).where(sessions.c.session_id == 1)
        ).scalar_one()
        connection.execute(
            sessions.update().where(sessions.c.session_id == 2).values(session_date=recorded_date)
        )
    for selected_plan, session_id in ((plan, 1), (other, 2)):
        slot = load_scheduled_workouts(engine, selected_plan.plan_id, start, start)[0]
        assign_scheduled_session(engine, slot.day_id, start, session_id)
    app = start_app(schedule_data)
    assert app.button(key="history_session_link_1").label == "Edit plan link"
    assert app.button(key="history_session_link_2").label == "Edit plan link"
    assert app.button(key="history_session_tools_1")
    assert app.button(key="history_session_tools_2")
    assert not any(box.key.startswith("match_target_") for box in app.selectbox)
    app.button(key="history_session_link_2").click().run()
    assert not app.exception and not app.error
    app.button(key="history_link_2_unlink").click().run()
    assert not app.exception and not app.error
    assert set(load_plan_session_links(engine)) == {1}


def test_no_plans_explains_how_to_enable_linking(schedule_data):
    from db.training_plans import delete_training_plan

    engine, _, plan, _ = schedule_data
    assert delete_training_plan(engine, plan.plan_id)
    app = start_app(schedule_data)
    app.button(key="history_session_link_1").click().run()
    assert not app.exception and not app.error
    assert any("Create a training plan" in info.value for info in app.info)


def test_unavailable_link_storage_keeps_recorded_session_readable(schedule_data, monkeypatch):
    def fail(*args, **kwargs):
        raise OperationalError("load", {}, RuntimeError("unavailable"))

    monkeypatch.setattr(DataManager, "load_session_plan_assignments", fail)
    app = start_app(schedule_data)
    assert app.button(key="history_session_link_1").disabled
    assert any('class="history-exercise-list-content"' in item.value for item in app.markdown)
