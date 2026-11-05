"""Bodyweight load snapshots, safe migration and atomic persistence."""
from dataclasses import FrozenInstanceError

import pandas as pd
import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from data_manager import DataManager
from db.migrations import v006_set_loads
from db.plan_adherence import _recorded, actual_exercises, actual_sets
from db.queries import get_all_sets, get_sets_raw
from db.set_classifications import load_session_sets
from db.set_loads import loads, save_session_set_loads, set_load_storage_ready
from mapper import map_workout_set
from models.set_load import SetLoad
from models.workout_set import WorkoutSet
from test_plan_schedule import schedule_data


@pytest.mark.parametrize("load,expected", [
    (SetLoad("external", 60), 60),
    (SetLoad("bodyweight", 0, 80), 80),
    (SetLoad("bodyweight", 10, 80), 90),
    (SetLoad("assisted_bodyweight", 0, 80, 20), 60),
    (SetLoad("assisted_bodyweight", 10, 80, 20), 70),
    (SetLoad("assisted_bodyweight", 0, 80, None), None),
    (SetLoad("bodyweight"), None),
])
def test_total_load(load, expected):
    assert load.total_load_kg == expected


@pytest.mark.parametrize("values", [
    {"load_type": "unknown"},
    {"load_type": "external", "external_weight_kg": -1},
    {"load_type": "external", "external_weight_kg": float("nan")},
    {"load_type": "external", "external_weight_kg": float("inf")},
    {"load_type": "bodyweight", "body_mass_kg": 0},
    {"load_type": "bodyweight", "body_mass_kg": -80},
    {"load_type": "bodyweight", "body_mass_kg": True},
    {"load_type": "bodyweight", "body_mass_kg": float("inf")},
    {"load_type": "bodyweight", "body_mass_kg": 1e308, "external_weight_kg": 1e308},
    {"load_type": "bodyweight", "assistance_kg": 20},
    {"load_type": "bodyweight", "assistance_kg": None},
    {"load_type": "external", "body_mass_kg": 80},
    {"load_type": "assisted_bodyweight", "assistance_kg": 0},
    {"load_type": "assisted_bodyweight", "body_mass_kg": 80, "assistance_kg": 90},
    {"load_type": "assisted_bodyweight", "assistance_kg": -1},
    {"load_type": "assisted_bodyweight", "assistance_kg": float("nan")},
])
def test_invalid_load_is_rejected(values):
    with pytest.raises(ValueError):
        SetLoad(**values)


def test_snapshot_is_immutable_and_set_weight_must_match():
    load = SetLoad("bodyweight", 5, 80)
    with pytest.raises(FrozenInstanceError):
        load.body_mass_kg = 90
    with pytest.raises(ValueError, match="match"):
        WorkoutSet(1, 1, 0, 80, None, 40, load=load)
    assert WorkoutSet(1, 1, 0, 5, None, 40, load=load).load.total_load_kg == 85


def test_mapper_keeps_legacy_convention_unknown_and_preserves_unknown_assistance():
    row = dict(workout_exercise_id=1, set_number=1, repetitions=0, weight=0, duration_seconds=40, rir=None)
    assert map_workout_set(row).load is None
    assert map_workout_set({**row, "load_type": float("nan")}).load is None
    mapped = map_workout_set({**row, "load_type": "assisted_bodyweight", "body_mass_kg": 80,
                             "assistance_kg": float("nan")})
    assert mapped.load.total_load_kg is None


def seed_sets(schedule_data):
    engine = schedule_data[0]
    with engine.begin() as connection:
        # Fixture catalog lacks the UI's body_part column.
        connection.exec_driver_sql("ALTER TABLE exercises ADD COLUMN body_part VARCHAR")
        connection.execute(actual_exercises.insert(), [
            {"workout_exercise_id": 100, "session_id": 1, "exercise_id": 1},
            {"workout_exercise_id": 200, "session_id": 2, "exercise_id": 1},
        ])
        connection.execute(actual_sets.insert(), [
            {"set_id": 1, "workout_exercise_id": 100, "set_number": 1, "repetitions": 0, "weight": 0, "duration_seconds": 40},
            {"set_id": 2, "workout_exercise_id": 100, "set_number": 2, "repetitions": 0, "weight": 0, "duration_seconds": 30},
            {"set_id": 3, "workout_exercise_id": 200, "set_number": 1, "repetitions": 8, "weight": 60, "duration_seconds": None},
        ])
    return engine


def test_roundtrip_through_raw_ui_session_and_plan_readers(schedule_data):
    engine = seed_sets(schedule_data)
    manager = object.__new__(DataManager)
    manager.engine = engine
    assert manager.set_load_storage_ready()
    manager.save_session_set_loads(1, {1: SetLoad("bodyweight", 10, 80),
                                      2: SetLoad("assisted_bodyweight", 0, 80, 20)})
    for frame in (get_sets_raw(engine), get_all_sets(engine), load_session_sets(engine, 1)):
        rows = [map_workout_set(row) for row in frame.to_dict("records")]
        explicit = [row for row in rows if row.load is not None]
        assert [row.load.total_load_kg for row in explicit] == [90, 60]
        assert [row.weight for row in explicit] == [10, 0]
    with engine.connect() as connection:
        recorded = _recorded(connection, {1, 2})
    by_id = {row.workout_exercise_id: row for row in recorded}
    assert by_id[100].sets[0].load == SetLoad("bodyweight", 10, 80)
    assert by_id[200].sets[0].load is None
    assert by_id[200].sets[0].weight == 60


def test_snapshot_does_not_follow_later_body_measurements(schedule_data):
    engine = seed_sets(schedule_data)
    save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 0, 80)})
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE body_composition (measurement_date DATE, weight FLOAT)")
        connection.exec_driver_sql("INSERT INTO body_composition VALUES ('2026-01-01', 80), ('2026-12-01', 90)")
        connection.exec_driver_sql("UPDATE body_composition SET weight=100")
    recorded = map_workout_set(load_session_sets(engine, 1).iloc[0].to_dict())
    assert recorded.load.body_mass_kg == recorded.load.total_load_kg == 80


def test_migration_preserves_existing_weights_and_optional_schema_readers(schedule_data):
    engine = seed_sets(schedule_data)
    with engine.begin() as connection:
        loads.drop(connection)
    assert not set_load_storage_ready(engine)
    for frame in (get_sets_raw(engine), get_all_sets(engine), load_session_sets(engine, 1)):
        assert frame.load_type.isna().all()
        assert all(map_workout_set(row).load is None for row in frame.to_dict("records"))
    with engine.connect() as connection:
        assert _recorded(connection, {1})[0].sets[0].load is None
    with pytest.raises(ValueError, match="migration"):
        save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 0, 80)})
    with engine.begin() as connection:
        v006_set_loads.apply(connection)
        assert connection.execute(select(actual_sets.c.weight).order_by(actual_sets.c.set_id)).scalars().all() == [0, 0, 60]
        assert connection.execute(select(loads)).all() == []


def test_cross_session_corrections_are_rejected_before_any_write(schedule_data):
    engine = seed_sets(schedule_data)
    with pytest.raises(ValueError, match="selected session"):
        save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 5, 80), 3: SetLoad("external", 100)})
    with engine.connect() as connection:
        assert connection.execute(select(loads)).all() == []
        assert connection.execute(select(actual_sets.c.weight).where(actual_sets.c.set_id == 1)).scalar_one() == 0


def test_failure_rolls_back_metadata_and_external_weight_together(schedule_data):
    engine = seed_sets(schedule_data)
    save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 5, 80)})

    def fail_second_insert(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO workout_set_loads") and parameters[0] == 2:
            raise RuntimeError("Simulated write failure")

    event.listen(engine, "before_cursor_execute", fail_second_insert)
    try:
        with pytest.raises(RuntimeError, match="Simulated"):
            save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 10, 81), 2: SetLoad("bodyweight", 10, 81)})
    finally:
        event.remove(engine, "before_cursor_execute", fail_second_insert)
    rows = load_session_sets(engine, 1)
    assert map_workout_set(rows.iloc[0].to_dict()).load == SetLoad("bodyweight", 5, 80)
    assert rows.iloc[1].weight == 0
    assert pd.isna(rows.iloc[1].load_type)


def test_removing_convention_preserves_weight_and_set_delete_cascades(schedule_data):
    engine = seed_sets(schedule_data)
    save_session_set_loads(engine, 1, {1: SetLoad("bodyweight", 10, 80), 2: SetLoad("bodyweight", 5, 80)})
    save_session_set_loads(engine, 1, {1: None})
    row = map_workout_set(load_session_sets(engine, 1).iloc[0].to_dict())
    assert row.load is None and row.weight == 10
    with engine.begin() as connection:
        connection.execute(actual_sets.delete().where(actual_sets.c.set_id == 2))
        assert connection.execute(select(loads)).all() == []


@pytest.mark.parametrize("values", [
    {"load_type": "invalid", "body_mass_kg": None, "assistance_kg": 0},
    {"load_type": "bodyweight", "body_mass_kg": 0, "assistance_kg": 0},
    {"load_type": "external", "body_mass_kg": 80, "assistance_kg": 0},
    {"load_type": "bodyweight", "body_mass_kg": 80, "assistance_kg": None},
    {"load_type": "assisted_bodyweight", "body_mass_kg": 80, "assistance_kg": -1},
])
def test_database_rejects_inconsistent_context(schedule_data, values):
    engine = seed_sets(schedule_data)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(loads.insert().values(set_id=1, **values))
