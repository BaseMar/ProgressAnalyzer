"""Real Streamlit reruns saving plan snapshots to an isolated database."""

from datetime import date

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from db.migrate import migrate
from db.training_plans import load_training_plan_versions, load_training_plans

APP = """
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
"""


@pytest.fixture
def plan_engine():
    engine = create_engine(
        "sqlite://", future=True, poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = MetaData()
    catalog = Table(
        "exercises",
        metadata,
        Column("exercise_id", Integer, primary_key=True),
        Column("exercise_name", String),
    )
    Table("workout_sessions", metadata, Column("session_id", Integer, primary_key=True))
    Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True))
    Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True))
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(
            catalog.insert(),
            [
                {"exercise_id": 1, "exercise_name": "Bench Press"},
                {"exercise_id": 2, "exercise_name": "Plank"},
            ],
        )
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
    fields = {
        "Sets": "sets",
        "From": "minimum",
        "To": "maximum",
        "RIR": "rir",
        "Increment": "increment",
    }
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
    app.run()
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
    fresh.selectbox(key="adherence_plan").select(saved.plan_id).run()
    assert not fresh.exception
    assert not fresh.text_input
    fresh.button(key=f"plan_edit_{saved.version_id}").click().run()
    assert fresh.text_input(key=f"plan_editor_{saved.version_id}_name").value == saved.draft.name


def test_revision_preserves_old_snapshot(plan_engine):
    app = start_app(plan_engine)
    create_plan(app)
    old = load_training_plans(plan_engine)[0]
    app.button(key=f"plan_edit_{old.version_id}").click().run()
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


def test_delete_requires_confirmation_and_last_plan_returns_to_creation(plan_engine):
    app = start_app(plan_engine)
    create_plan(app)
    saved = load_training_plans(plan_engine)[0]
    assert app.button(key=f"plan_delete_{saved.plan_id}").disabled
    app.checkbox(key=f"plan_delete_confirm_{saved.plan_id}").check().run()
    assert not app.button(key=f"plan_delete_{saved.plan_id}").disabled
    app.button(key=f"plan_delete_{saved.plan_id}").click().run()
    assert not app.exception and not app.error
    assert load_training_plans(plan_engine) == []
    assert app.success and "Plan deleted" in app.success[0].value
    assert app.text_input(key="plan_editor_new_name")
    assert "active_plan_id" not in app.session_state
    assert "adherence_plan" not in app.session_state
    assert load_training_plans(plan_engine) == []
    fresh = start_app(plan_engine)
    assert fresh.text_input(key="plan_editor_new_name")


def test_delete_selects_remaining_plan_and_clears_deleted_draft(plan_engine):
    from dataclasses import replace

    from db.training_plans import save_training_plan

    app = start_app(plan_engine)
    create_plan(app)
    saved = load_training_plans(plan_engine)[0]
    other = save_training_plan(plan_engine, replace(saved.draft, name="Other plan"))
    app.button(key=f"plan_edit_{saved.version_id}").click().run()
    app.text_input(key=f"plan_editor_{saved.version_id}_name").set_value("Unsaved edit")
    app.button(key=f"plan_edit_{saved.version_id}").click().run()
    app.checkbox(key=f"plan_delete_confirm_{saved.plan_id}").check().run()
    app.button(key=f"plan_delete_{saved.plan_id}").click().run()
    assert not app.exception and not app.error
    assert load_training_plans(plan_engine) == [other]
    assert app.selectbox(key="adherence_plan").value == other.plan_id
    assert app.session_state["active_plan_id"] == other.plan_id
    assert f"plan_editor_{saved.version_id}_draft" not in app.session_state
    assert app.button(key=f"plan_delete_{other.plan_id}").disabled


def test_failed_delete_keeps_plan_and_allows_retry(plan_engine, monkeypatch):
    from data_manager import DataManager

    app = start_app(plan_engine)
    create_plan(app)
    saved = load_training_plans(plan_engine)[0]
    original = DataManager.delete_training_plan

    def fail(*args, **kwargs):
        raise OperationalError("delete", {}, RuntimeError("unavailable"))

    monkeypatch.setattr(DataManager, "delete_training_plan", fail)
    app.checkbox(key=f"plan_delete_confirm_{saved.plan_id}").check().run()
    app.button(key=f"plan_delete_{saved.plan_id}").click().run()
    assert not app.exception
    assert "could not be deleted" in app.error[0].value
    assert load_training_plans(plan_engine) == [saved]
    monkeypatch.setattr(DataManager, "delete_training_plan", original)
    app.button(key=f"plan_delete_{saved.plan_id}").click().run()
    assert not app.exception and not app.error
    assert load_training_plans(plan_engine) == []


def test_add_and_remove_workouts_keeps_remaining_inputs_and_time_targets(plan_engine):
    app = start_app(plan_engine)
    add_key = "plan_editor_new_add"
    name_key = "plan_editor_new_day_0_name"
    assert app.button(key=add_key).disabled
    app.text_input(key="plan_editor_new_name").set_value("Core")
    app.text_input(key=name_key).set_value("Strength").run()
    assert not app.button(key=add_key).disabled
    app.text_input(key=name_key).set_value("   ").run()
    assert app.button(key=add_key).disabled
    assert any("Enter a workout name for Monday" in field.proto.body for field in app.get("html"))
    assert len(app.session_state["plan_editor_new_draft"]["days"]) == 1

    app.text_input(key=name_key).set_value("Strength").run()
    app.button(key=add_key).click().run()
    assert app.text_input(key="plan_editor_new_name").value == "Core"
    weekdays = app.selectbox(key="plan_editor_new_day_1_weekday")
    assert weekdays.value == 1
    assert "Monday" not in weekdays.options
    assert any("Workout draft added for Tuesday" in item.value for item in app.success)
    assert app.button(key=add_key).disabled
    app.text_input(key="plan_editor_new_day_1_name").set_value("Core A")
    app.selectbox(key="plan_editor_new_day_1_weekday").select(2)
    edit_rows(
        app,
        "plan_editor_new_day_1_exercises",
        {
            "Exercise": "Plank · #2",
            "From": 30,
            "To": 60,
            "Unit": "seconds",
            "RIR": 2,
        },
    )
    app.selectbox(key="plan_editor_new_active_day").select(0).run()
    app.button(key="plan_editor_new_day_0_remove").click().run()
    assert not app.exception
    assert any("Removed Strength" in item.value for item in app.success)
    assert "Monday" in app.selectbox(key="plan_editor_new_day_1_weekday").options
    app.button(key="plan_editor_new_save").click().run()
    assert not app.error, [error.value for error in app.error]
    day = load_training_plans(plan_engine)[0].draft.days[0]
    assert day.name == "Core A"
    assert day.weekday == 2
    assert day.exercises[0].target_unit == "seconds"
    assert day.exercises[0].target_min == 30
    assert day.exercises[0].target_rir == 2


def test_legacy_duplicate_workouts_can_be_edited_but_cannot_be_saved_with_same_day(plan_engine):
    from db.training_plans import save_training_plan
    from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft

    migrate(plan_engine, apply=True)
    exercise = (PlannedExercise(1, 3, 6, 10),)
    old = save_training_plan(
        plan_engine,
        TrainingPlanDraft(
            "Two Monday workouts",
            date.today(),
            (TrainingDay("Upper A", 0, exercise), TrainingDay("Upper B", 0, exercise)),
        ),
    )
    app = start_app(plan_engine, ready=False)
    app.button(key=f"plan_edit_{old.version_id}").click().run()
    scope = f"plan_editor_{old.version_id}"
    assert app.button(key=f"{scope}_add").disabled
    assert any(
        "More than one workout is planned for Monday" in field.proto.body
        for field in app.get("html")
    )
    assert len(app.session_state[f"{scope}_draft"]["days"]) == 2
    assert app.button(key=f"{scope}_save").disabled
    assert load_training_plan_versions(plan_engine, old.plan_id) == [old]

    app.selectbox(key=f"{scope}_day_0_weekday").select(1).run()
    app.button(key=f"{scope}_save").click().run()
    assert not app.exception and not app.error
    assert [day.weekday for day in load_training_plans(plan_engine)[0].draft.days] == [1, 0]


def test_invalid_range_stays_in_editor_and_does_not_save(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Upper")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Upper A")
    edit_rows(
        app,
        "plan_editor_new_day_0_exercises",
        {
            "Exercise": "Bench Press · #1",
            "From": 12,
            "To": 6,
        },
    )
    app.run()
    assert not app.exception
    assert app.button(key="plan_editor_new_save").disabled
    assert any("minimum cannot exceed" in field.proto.body for field in app.get("html"))
    assert load_training_plans(plan_engine) == []
    assert app.text_input(key="plan_editor_new_name").value == "Upper"
    app.number_input(key="plan_editor_new_day_0_ex_0_maximum").set_value(12).run()
    assert not app.button(key="plan_editor_new_save").disabled


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
    app.number_input(key="plan_editor_new_day_0_ex_0_rir").set_value(0).run()
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


def test_empty_workout_can_be_rebuilt_without_losing_plan_details(plan_engine):
    app = start_app(plan_engine)
    app.text_input(key="plan_editor_new_name").set_value("Rebuilt plan")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Core")
    app.button(key="plan_editor_new_day_0_ex_0_remove").click().run()
    assert not app.exception
    assert not app.number_input
    app.button(key="plan_editor_new_day_0_add_exercise").click().run()
    assert app.radio(key="plan_editor_new_day_0_active_exercise").value == 1
    app.selectbox(key="plan_editor_new_day_0_ex_1_exercise_id").select(2)
    app.selectbox(key="plan_editor_new_day_0_ex_1_unit").select("seconds")
    app.number_input(key="plan_editor_new_day_0_ex_1_minimum").set_value(45)
    app.number_input(key="plan_editor_new_day_0_ex_1_maximum").set_value(45).run()
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception and not app.error
    saved = load_training_plans(plan_engine)[0]
    assert saved.draft.name == "Rebuilt plan"
    assert saved.draft.days[0].name == "Core"
    assert saved.draft.days[0].exercises[0].target_min == 45
    assert saved.draft.days[0].exercises[0].target_unit == "seconds"


def test_target_preview_tracks_selected_exercise_and_keeps_zero_reserve(plan_engine):
    app = start_app(plan_engine)
    app.selectbox(key="plan_editor_new_day_0_ex_0_exercise_id").select(1)
    app.number_input(key="plan_editor_new_day_0_ex_0_sets").set_value(4)
    app.number_input(key="plan_editor_new_day_0_ex_0_minimum").set_value(8)
    app.number_input(key="plan_editor_new_day_0_ex_0_maximum").set_value(8)
    app.number_input(key="plan_editor_new_day_0_ex_0_rir").set_value(0)
    app.button(key="plan_editor_new_day_0_add_exercise").click().run()
    app.selectbox(key="plan_editor_new_day_0_ex_1_unit").select("seconds")
    app.number_input(key="plan_editor_new_day_0_ex_1_minimum").set_value(30)
    app.number_input(key="plan_editor_new_day_0_ex_1_maximum").set_value(60)
    app.run()
    preview = next(
        item.value for item in app.markdown if 'class="plan-target-preview"' in item.value
    )
    assert "3 × 30–60 seconds" in preview
    assert "RIR 0" not in preview
    app.radio(key="plan_editor_new_day_0_active_exercise").set_value(0).run()
    preview = next(
        item.value for item in app.markdown if 'class="plan-target-preview"' in item.value
    )
    assert "4 × 8 reps" in preview
    assert "RIR 0" in preview
