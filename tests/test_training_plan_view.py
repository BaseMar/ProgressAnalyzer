"""Real Streamlit reruns saving plan snapshots to an isolated database."""

from datetime import date

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, event
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from db.migrate import migrate
from db.training_plans import load_training_plans, load_training_plan_versions


APP = '''
import streamlit as st
from data_manager import DataManager
from models.exercise import Exercise
from ui.training_plan_view import TrainingPlanView

manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
TrainingPlanView([
    Exercise(1, "Bench Press", None, "Chest"),
    Exercise(2, "Plank", None, "Abs"),
], manager).render()
'''


@pytest.fixture
def plan_engine():
    engine = create_engine("sqlite://", future=True, poolclass=StaticPool,
                           connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = MetaData()
    catalog = Table("exercises", metadata,
        Column("exercise_id", Integer, primary_key=True), Column("exercise_name", String),
    )
    Table("workout_sessions", metadata, Column("session_id", Integer, primary_key=True))
    Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True))
    Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True))
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(catalog.insert(), [
            {"exercise_id": 1, "exercise_name": "Bench Press"},
            {"exercise_id": 2, "exercise_name": "Plank"},
        ])
    yield engine
    engine.dispose()


def start_app(engine, ready=True):
    if ready:
        migrate(engine, apply=True)
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.run()
    assert not app.exception
    return app


def edit_rows(app, key, changes):
    prefix = key.removesuffix("_exercises") + "_ex_0"
    fields = {"Sets": "sets", "From": "minimum", "To": "maximum", "RIR": "rir", "Increment": "increment"}
    for name, value in changes.items():
        if name == "Exercise":
            app.selectbox(key=f"{prefix}_exercise_id").select(1 if value.startswith("Bench") else 2)
        elif name == "Unit":
            app.selectbox(key=f"{prefix}_unit").select(value)
        else:
            app.number_input(key=f"{prefix}_{fields[name]}").set_value(value)


def create_plan(app):
    app.text_input(key="plan_editor_new_name").set_value("Upper / Core")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Upper A")
    edit_rows(app, "plan_editor_new_day_0_exercises", {"Exercise": "Bench Press · #1"})
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception
    assert not app.error


def test_create_plan_persists_and_is_visible_after_a_fresh_page_load(plan_engine):
    app = start_app(plan_engine)
    create_plan(app)
    saved = load_training_plans(plan_engine)[0]
    assert saved.draft.name == "Upper / Core"
    assert saved.draft.days[0].exercises[0].exercise_id == 1
    assert saved.draft.days[0].exercises[0].target_rir is None
    assert saved.draft.days[0].exercises[0].target_min == 6
    assert app.success
    fresh = start_app(plan_engine)
    fresh.selectbox(key="training_plan_picker").select(saved.plan_id).run()
    assert not fresh.exception
    assert not fresh.text_input
    fresh.toggle(key=f"plan_edit_{saved.version_id}").set_value(True).run()
    assert fresh.text_input(key=f"plan_editor_{saved.version_id}_name").value == saved.draft.name


def test_revision_preserves_old_snapshot(plan_engine):
    app = start_app(plan_engine)
    create_plan(app)
    old = load_training_plans(plan_engine)[0]
    app.toggle(key=f"plan_edit_{old.version_id}").set_value(True).run()
    scope = f"plan_editor_{old.version_id}"
    app.text_input(key=f"{scope}_name").set_value("Upper / Core v2")
    edit_rows(app, f"{scope}_day_0_exercises", {"Sets": 4})
    app.button(key=f"{scope}_save").click().run()
    assert not app.exception
    assert not app.error
    history = load_training_plan_versions(plan_engine, old.plan_id)
    assert history[0] == old
    assert len(history) == 2
    assert history[1].draft.days[0].exercises[0].set_count == 4
    assert history[1].draft.effective_from > date.today()


def test_add_and_remove_workouts_keeps_remaining_inputs_and_time_targets(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Core")
    app.button(key="plan_editor_new_add").click().run()
    assert app.text_input(key="plan_editor_new_name").value == "Core"
    app.text_input(key="plan_editor_new_day_1_name").set_value("Core A")
    app.selectbox(key="plan_editor_new_day_1_weekday").select(2)
    edit_rows(app, "plan_editor_new_day_1_exercises", {
        "Exercise": "Plank · #2", "From": 30, "To": 60, "Unit": "seconds", "RIR": 2,
    })
    app.selectbox(key="plan_editor_new_active_day").select(0).run()
    app.button(key="plan_editor_new_day_0_remove").click().run()
    assert not app.exception
    app.button(key="plan_editor_new_save").click().run()
    assert not app.error, [error.value for error in app.error]
    day = load_training_plans(plan_engine)[0].draft.days[0]
    assert day.name == "Core A"
    assert day.weekday == 2
    assert day.exercises[0].target_unit == "seconds"
    assert day.exercises[0].target_min == 30
    assert day.exercises[0].target_rir == 2


def test_invalid_range_stays_in_editor_and_does_not_save(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Upper")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Upper A")
    edit_rows(app, "plan_editor_new_day_0_exercises", {
        "Exercise": "Bench Press · #1", "From": 12, "To": 6,
    })
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception
    assert "minimum cannot exceed" in app.error[0].value
    assert load_training_plans(plan_engine) == []
    assert app.text_input(key="plan_editor_new_name").value == "Upper"


def test_missing_migration_shows_setup_state_without_crashing(plan_engine):
    app = start_app(plan_engine, ready=False)
    assert "setup" in app.info[0].value
    assert len(app.text_input) == 0


def test_added_exercise_rows_save_in_requested_order(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Upper / Core")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Mixed")
    app.selectbox(key="plan_editor_new_day_0_ex_0_exercise_id").select(1)
    app.button(key="plan_editor_new_day_0_add_exercise").click().run()
    app.selectbox(key="plan_editor_new_day_0_ex_1_exercise_id").select(2)
    app.number_input(key="plan_editor_new_day_0_ex_1_sets").set_value(2)
    app.number_input(key="plan_editor_new_day_0_ex_1_minimum").set_value(30)
    app.number_input(key="plan_editor_new_day_0_ex_1_maximum").set_value(60)
    app.selectbox(key="plan_editor_new_day_0_ex_1_unit").select("seconds")
    app.button(key="plan_editor_new_day_0_ex_1_up").click().run()
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception
    assert not app.error
    items = load_training_plans(plan_engine)[0].draft.days[0].exercises
    assert [item.exercise_id for item in items] == [2, 1]
    assert items[0].target_unit == "seconds"
    assert items[1].target_unit == "reps"


def test_switching_workouts_preserves_unsaved_fields_and_uses_no_spreadsheet(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Weekly reference")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Upper A")
    app.selectbox(key="plan_editor_new_day_0_ex_0_exercise_id").select(1)
    app.number_input(key="plan_editor_new_day_0_ex_0_minimum").set_value(8)
    app.number_input(key="plan_editor_new_day_0_ex_0_rir").set_value(0)
    app.button(key="plan_editor_new_add").click().run()
    app.text_input(key="plan_editor_new_day_1_name").set_value("Core")
    app.selectbox(key="plan_editor_new_day_1_ex_0_exercise_id").select(2)
    app.selectbox(key="plan_editor_new_active_day").select(0).run()
    assert app.text_input(key="plan_editor_new_day_0_name").value == "Upper A"
    assert app.number_input(key="plan_editor_new_day_0_ex_0_minimum").value == 8
    assert app.number_input(key="plan_editor_new_day_0_ex_0_rir").value == 0
    assert not app.dataframe
    app.button(key="plan_editor_new_save").click().run()
    assert not app.error
    saved = load_training_plans(plan_engine)[0]
    assert [day.name for day in saved.draft.days] == ["Upper A", "Core"]
    assert saved.draft.days[0].exercises[0].target_rir == 0
