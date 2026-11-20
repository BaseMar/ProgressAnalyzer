"""Header tools edit only the selected session through one dialog."""

import pytest
from sqlalchemy import select

from data_manager import DataManager
from db.plan_adherence import actual_exercises, actual_sets, matches
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.set_loads import loads
from db.training_plans import days, exercises
from test_plan_schedule import schedule_data as schedule_data
from test_session_plan_link import start_app


@pytest.fixture
def tools_data(schedule_data):
    engine = schedule_data[0]
    with engine.begin() as connection:
        connection.execute(
            actual_exercises.insert().values(workout_exercise_id=100, session_id=1, exercise_id=1)
        )
        connection.execute(
            actual_sets.insert(),
            [
                dict(
                    set_id=101,
                    workout_exercise_id=100,
                    set_number=1,
                    repetitions=8,
                    weight=60.0,
                    rir=2,
                ),
                dict(
                    set_id=102,
                    workout_exercise_id=100,
                    set_number=2,
                    repetitions=6,
                    weight=65.0,
                    rir=0,
                ),
            ],
        )
    return schedule_data


def open_tools(app, session_id=1, tab="Set labels"):
    app.button(key=f"history_session_tools_{session_id}").click().run()
    assert not app.exception and not app.error
    app.session_state[f"history_tools_tab_{session_id}"] = tab
    app.run()
    assert not app.exception and not app.error
    return app


def test_tools_are_absent_until_opened_and_label_corrections_persist(tools_data):
    app = start_app(tools_data)
    assert not any(item.label == "Session tools" for item in app.expander)
    assert not app.get("data_editor") and not app.button(key="history_session_tools_1").disabled
    open_tools(app)
    assert not any(toggle.key == "set_exception_1" for toggle in app.toggle)
    app.session_state["set_types_1"] = {
        "edited_rows": {0: {"Type": "Warm-up"}},
        "added_rows": [],
        "deleted_rows": [],
    }
    app.button(key="save_set_types_1").click().run()
    assert not app.exception and not app.error
    assert bool(DataManager(engine=tools_data[0]).load_session_sets(1).iloc[0].is_warmup)
    assert app.session_state["history_tools_session"][0] == 1


def test_load_correction_persists_in_the_selected_session(tools_data):
    app = open_tools(start_app(tools_data), tab="Set load")
    assert not any(toggle.key == "edit_load_1" for toggle in app.toggle)
    app.selectbox(key="load_1_101_kind").select("external").run()
    app.number_input(key="load_1_101_weight").set_value(72.5)
    app.button(key="load_1_101_save").click().run()
    assert not app.exception and not app.error
    with tools_data[0].connect() as connection:
        rows = connection.execute(select(actual_sets).order_by(actual_sets.c.set_id)).all()
        assert [row.weight for row in rows] == [72.5, 65.0]
        assert len(connection.execute(select(loads)).all()) == 1


def test_unlinked_session_can_switch_from_tools_to_link_dialog(tools_data):
    app = open_tools(start_app(tools_data), tab="Replacements")
    assert any("Link this session" in item.value for item in app.info)
    app.button(key="history_tools_link_1").click().run()
    assert not app.exception and not app.error
    assert "history_tools_session" not in app.session_state
    assert app.selectbox(key="history_link_1_plan")


def test_linked_session_replacements_are_available_without_another_expander(tools_data):
    engine, start, plan, _ = tools_data
    slot = load_scheduled_workouts(engine, plan.plan_id, start, start)[0]
    assign_scheduled_session(engine, slot.day_id, start, 1)
    with engine.begin() as connection:
        target_id = connection.execute(
            select(exercises.c.plan_exercise_id)
            .join(days)
            .where(days.c.version_id == plan.version_id)
        ).scalar_one()
        connection.exec_driver_sql(
            "INSERT INTO exercises (exercise_id, exercise_name) VALUES (2, 'Chest Press')"
        )
        connection.execute(
            actual_exercises.update()
            .where(actual_exercises.c.workout_exercise_id == 100)
            .values(exercise_id=2)
        )
    app = open_tools(start_app(tools_data), tab="Replacements")
    assert not any(item.label == "Confirm exercise replacements" for item in app.expander)
    assert not any(box.key == "match_workout_session_1" for box in app.selectbox)
    app.selectbox(key=f"replacement_1_{target_id}_exercise").select(100).run()
    app.button(key=f"replacement_1_{target_id}_confirm").click().run()
    assert not app.exception and not app.error
    with engine.connect() as connection:
        assert len(connection.execute(select(matches)).all()) == 1


def test_delete_session_closes_tools_and_keeps_other_sessions(tools_data):
    engine, _, _, sessions = tools_data
    app = open_tools(start_app(tools_data), tab="Delete session")
    app.button(key="del_1").click().run()
    assert not app.exception and not app.error
    assert "history_tools_session" not in app.session_state
    assert app.success[0].value == "Session deleted."
    with engine.connect() as connection:
        assert set(connection.execute(select(sessions.c.session_id)).scalars()) == {2, 3}
        assert connection.execute(select(actual_exercises)).all() == []
        assert connection.execute(select(actual_sets)).all() == []


def test_failed_delete_keeps_dialog_open_and_allows_retry(tools_data, monkeypatch):
    app = open_tools(start_app(tools_data), tab="Delete session")
    original = DataManager.delete_session
    monkeypatch.setattr(DataManager, "delete_session", lambda *args: False)
    app.button(key="del_1").click().run()
    assert not app.exception
    assert "could not be deleted" in app.error[0].value
    assert app.session_state["history_tools_session"][0] == 1
    monkeypatch.setattr(DataManager, "delete_session", original)
    app.button(key="del_1").click().run()
    assert not app.exception and not app.error


def test_tools_work_independently_for_two_sessions_on_the_same_day(tools_data):
    engine, _, _, sessions = tools_data
    with engine.begin() as connection:
        day = connection.execute(
            select(sessions.c.session_date).where(sessions.c.session_id == 1)
        ).scalar_one()
        connection.execute(
            sessions.update().where(sessions.c.session_id == 2).values(session_date=day)
        )
    app = open_tools(start_app(tools_data), session_id=2)
    assert any("No sets in this session" in item.value for item in app.caption)
    assert not app.get("data_editor")
    app.session_state["history_tools_session"] = None
    app.run()
    open_tools(app, session_id=1)
    assert app.button(key="save_set_types_1")
