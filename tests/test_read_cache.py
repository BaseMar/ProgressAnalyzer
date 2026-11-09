"""Bounded reads, current write results and unchanged recommendation semantics."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from contextvars import Context
from dataclasses import replace
from datetime import timedelta
from threading import Barrier, current_thread
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, text

from data_loader import load_data
from data_manager import DataManager
from db.plan_adherence import load_plan_performance
from db.plan_schedule import load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.read_cache import has_table, install_read_invalidation, read_cached, read_scope
from db.training_plans import load_training_plan_versions, save_training_plan
from models.set_load import SetLoad
from scripts.baseline_fixture import AS_OF, create_fixture
from scripts.baseline_snapshot import capture_snapshot, snapshot_reference
from scripts.benchmark_project import ReadOnlyProbe
from test_starting_loads import choices


@pytest.fixture
def workload():
    engine, plan = create_fixture(weeks=2)
    try:
        yield engine, plan
    finally:
        load_data.clear()
        engine.dispose()


def test_shared_reads_preserve_the_entire_semantic_snapshot(workload):
    engine, plan = workload
    expected = snapshot_reference(capture_snapshot(engine, plan))
    with read_scope():
        assert snapshot_reference(capture_snapshot(engine, plan)) == expected


def test_recommendations_preserve_caller_owned_transaction_adapters(workload):
    engine, plan = workload
    slot = load_scheduled_workouts(engine, plan.plan_id, AS_OF, AS_OF)[0]
    expected = load_workout_recommendations(engine, plan.plan_id, slot.day_id, AS_OF, as_of=AS_OF)
    with engine.connect() as connection:
        adapter = SimpleNamespace(connect=lambda: nullcontext(connection))
        assert (
            load_workout_recommendations(adapter, plan.plan_id, slot.day_id, AS_OF, as_of=AS_OF)
            == expected
        )
        assert connection.in_transaction()


def test_versions_are_batched_and_repeated_history_reads_do_no_sql(workload):
    engine, plan = workload

    def measure_versions():
        statements = []

        def count(*args):
            statements.append(args[2])

        event.listen(engine, "before_cursor_execute", count)
        try:
            with read_scope():
                load_training_plan_versions(engine, plan.plan_id)
            return len(statements)
        finally:
            event.remove(engine, "before_cursor_execute", count)

    original_count = measure_versions()
    for offset in range(1, 5):
        with patch("db.training_plans.date") as clock:
            clock.today.return_value = AS_OF
            plan = save_training_plan(
                engine,
                replace(plan.draft, effective_from=AS_OF + timedelta(days=offset)),
                plan_id=plan.plan_id,
            )
    assert measure_versions() == original_count
    with ReadOnlyProbe(engine) as probe, read_scope():

        def action():
            return load_plan_performance(engine, plan.plan_id, AS_OF - timedelta(days=27), AS_OF)

        action()
        assert probe.measure(action)["sql_count"] == 0


def test_contexts_engines_and_scope_exit_never_share_results():
    engines = [create_engine("sqlite://") for _ in range(2)]
    calls = []

    @read_cached
    def read(engine):
        calls.append(engine)
        with engine.connect() as connection:
            return connection.exec_driver_sql("SELECT 1").scalar_one()

    try:
        with read_scope():
            read(engines[0])
            with read_scope():
                read(engines[0])
            assert len(calls) == 1
            read(engines[1])
            Context().run(lambda: read(engines[0]))
            assert len(calls) == 3
        read(engines[0])
        with pytest.raises(ValueError), read_scope():
            read(engines[0])
            raise ValueError("Render stopped")
        with read_scope():
            read(engines[0])
        assert len(calls) == 6
    finally:
        for engine in engines:
            engine.dispose()


def test_raw_writes_and_rollback_invalidate_schema_and_uncommitted_reads():
    engine = create_engine("sqlite://")

    @read_cached
    def read(connection):
        return connection.execute(text("SELECT value FROM sample")).scalar_one()

    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE sample (value INTEGER)")
            connection.exec_driver_sql("INSERT INTO sample VALUES (1)")
        with read_scope():
            with engine.connect() as connection:
                assert read(connection) == 1
                connection.exec_driver_sql("UPDATE sample SET value=2")
                assert read(connection) == 2
                connection.rollback()
                assert read(connection) == 1
                assert not has_table(connection, "added")
                connection.exec_driver_sql("CREATE TABLE added (id INTEGER)")
                assert has_table(connection, "added")
                connection.commit()
            with engine.connect() as connection:
                connection.execute(text("UPDATE sample SET value=3"))
                connection.commit()
                assert read(connection) == 3
    finally:
        engine.dispose()


def test_concurrent_renders_keep_their_own_cache_and_engine_listeners():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    install_read_invalidation(engine)
    barrier = Barrier(2, timeout=10)

    @read_cached
    def read(source):
        with source.connect() as connection:
            connection.exec_driver_sql("SELECT 1").scalar_one()
        return current_thread().name

    def render():
        for _ in range(20):
            with read_scope():
                first = read(engine)
                barrier.wait()
                assert read(engine) == first == current_thread().name
            barrier.wait()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(render) for _ in range(2)]
            for future in futures:
                future.result(timeout=15)
    finally:
        engine.dispose()


def test_saved_defaults_refresh_in_the_same_render(workload):
    engine, _ = workload
    manager = object.__new__(DataManager)
    manager.engine = engine
    upcoming, item, block, goals = choices()
    with read_scope():
        assert manager.load_starting_loads(upcoming, item, block) == ()
        manager.save_starting_loads(upcoming, item, block, goals)
        assert manager.load_starting_loads(upcoming, item, block) == goals


def test_input_cache_updates_after_import_correction_measurement_and_deletion(workload):
    engine, _ = workload
    with patch("data_manager.get_engine", return_value=engine):
        manager = DataManager()
        load_data.clear()
        before, _ = load_data()
        manager.add_workout_session(
            AS_OF,
            "Cache regression",
            [
                {
                    "exercise_id": 1,
                    "sets": [{"weight": 65.0, "reps": 8, "rir": 2}],
                }
            ],
        )
        after, _ = load_data()
        assert len(after.sets) == len(before.sets) + 1
        session_id = max(s.session_id for s in after.sessions)
        set_id = manager.load_session_sets(session_id).iloc[0].set_id
        manager.save_session_set_loads(session_id, {int(set_id): SetLoad("external", 70.0)})
        corrected, _ = load_data()
        assert corrected.sets[-1].weight == 70.0
        manager.save_set_classifications(session_id, {int(set_id): True})
        classified, _ = load_data()
        assert classified.sets[-1].is_warmup is True
        assert manager.add_body_composition(
            dict(
                date=AS_OF,
                weight=84.0,
                muscle_mass=36.0,
                fat_mass=15.0,
                water_mass=45.0,
                bf_percent=18.0,
                method="Synthetic",
            )
        )
        measured, _ = load_data()
        assert len(measured.body_composition) == len(before.body_composition) + 1
        assert manager.delete_session(session_id)
        deleted, _ = load_data()
        assert len(deleted.sets) == len(before.sets)


def test_plan_revision_and_links_refresh_cached_deload_context(workload):
    engine, plan = workload
    with patch("data_manager.get_engine", return_value=engine):
        manager = DataManager()
        load_data.clear()
        before, _ = load_data()
        # Change the block to its final week, then link a newly recorded slot.
        draft = replace(
            plan.draft,
            effective_from=AS_OF + timedelta(days=1),
            progression=replace(plan.draft.progression, block_start=AS_OF - timedelta(weeks=6)),
        )
        with patch("db.training_plans.date") as clock:
            clock.today.return_value = AS_OF
            revised = manager.save_training_plan(draft, plan_id=plan.plan_id)
        slot = next(
            s
            for s in load_scheduled_workouts(
                engine, plan.plan_id, AS_OF + timedelta(days=1), AS_OF + timedelta(days=7)
            )
            if s.version_id == revised.version_id
        )
        # Record it early: the scheduled deload context still applies.
        manager.add_workout_session(
            AS_OF,
            "Early deload",
            [
                {
                    "exercise_id": 1,
                    "sets": [{"weight": 40.0, "reps": 8, "rir": 4}],
                }
            ],
        )
        unlinked, _ = load_data()
        sid = max(s.session_id for s in unlinked.sessions)
        manager.assign_scheduled_session(slot.day_id, slot.scheduled_date, sid)
        linked, _ = load_data()
        assert len(linked.deload_exercise_ids) == len(before.deload_exercise_ids) + 1
        manager.unassign_scheduled_session(slot.day_id, slot.scheduled_date, sid)
        unlinked_again, _ = load_data()
        assert unlinked_again.deload_exercise_ids == before.deload_exercise_ids
