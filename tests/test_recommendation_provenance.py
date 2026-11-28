from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import time, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import inspect, select
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from db.bootstrap import ConnectionScope, bootstrap_database
from db.exercise_starting_history import load_exercise_starting_history
from db.migrate import MIGRATIONS, migrate
from db.read_cache import read_scope
from db.session_provenance import provenance
from db.set_classifications import classifications
from models.progression import SetGoal
from models.set_load import SetLoad
from models.training_plan import ProgressionSettings, TrainingDay
from test_bootstrap import fresh_engine as fresh_engine
from test_import_evidence_integrity import (
    PRESS,
    START,
    recommendation,
    record,
    saved_slot,
    workout_plan,
)
from test_import_evidence_integrity import (
    manager as manager,
)
from test_import_evidence_integrity import (
    upload_ui as upload_ui,
)
from ui.sidebar_upload import SidebarUpload


def describe(item):
    return (
        item.action,
        item.reason_code,
        item.evidence_session_ids,
        [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals],
    )


def revise(manager, plan, day, *, maximum=8, settings=None, step=2.5):
    item = replace(PRESS, target_min=6, target_max=maximum, weight_increment=step)
    with patch("db.training_plans.date") as clock:
        clock.today.return_value = START
        return manager.save_training_plan(
            replace(
                plan.draft,
                effective_from=day,
                days=(TrainingDay("Revised", 0, (item,)),),
                progression=settings,
            ),
            plan_id=plan.plan_id,
        )


def prepare(manager, plan, day, *, as_of=None):
    slot = saved_slot(manager, plan, day)
    return manager.prepare_plan_context(plan.plan_id, day, day, as_of=as_of or day).prepare_workout(
        slot.day_id, day
    )


def test_unlink_keeps_the_original_prescription(manager):
    plan = workout_plan(manager, TrainingDay("Original", 0, (PRESS,)))
    session = record(manager, START, 1, plan=plan)
    day = START + timedelta(weeks=1)
    revised = revise(manager, plan, day)
    expected = ("maintain", "prescription_changed", (session,), [(60, 6, 8)] * 3)
    assert describe(recommendation(manager, revised, day)) == expected
    original = manager.load_session_sets(session).copy(deep=True)

    slot = saved_slot(manager, plan, START)
    manager.unassign_scheduled_session(slot.day_id, START, session)
    assert manager.load_session_plan_assignments((session,)) == {}
    assert describe(recommendation(manager, revised, day)) == expected
    assert manager.load_session_sets(session).equals(original)

    # Relinking to an explicitly corrected prescription replaces the old source.
    corrected = workout_plan(
        manager, TrainingDay("Corrected", 0, (replace(PRESS, target_min=6, target_max=8),))
    )
    corrected_slot = saved_slot(manager, corrected, START)
    manager.assign_scheduled_session(corrected_slot.day_id, START, session)
    corrected_goal = ("increase_weight", "upper_range_confirmed", (session,), [(62.5, 6, 6)] * 3)
    assert describe(recommendation(manager, revised, day)) == corrected_goal
    manager.unassign_scheduled_session(corrected_slot.day_id, START, session)
    assert describe(recommendation(manager, revised, day)) == corrected_goal


def phased_plan(manager):
    plan = workout_plan(manager, TrainingDay("Block", 0, (PRESS,)))
    return revise(
        manager,
        plan,
        START + timedelta(weeks=1),
        maximum=12,
        settings=ProgressionSettings(START, 6),
    )


def test_unlinked_and_deleted_plan_deload_stays_out_of_history(manager):
    plan = phased_plan(manager)
    ordinary_day = START + timedelta(weeks=4)
    deload_day = START + timedelta(weeks=5)
    return_day = START + timedelta(weeks=6)
    ordinary = record(manager, ordinary_day, 1, (10, 10, 10), plan=plan)
    assert describe(recommendation(manager, plan, deload_day)) == (
        "deload",
        "scheduled_deload",
        (ordinary,),
        [(40, 10, 10)] * 3,
    )
    deload = record(
        manager, deload_day + timedelta(days=1), 1, (10, 10, 10), plan=plan, scheduled=deload_day
    )
    ids = manager.load_session_sets(deload).set_id.astype(int)
    manager.save_session_set_loads(deload, {set_id: SetLoad("external", 40) for set_id in ids})
    baseline = ("maintain", "resume_after_deload", (ordinary,), [(60, 10, 10)] * 3)
    assert describe(recommendation(manager, plan, return_day)) == baseline
    slot = saved_slot(manager, plan, deload_day)
    manager.unassign_scheduled_session(slot.day_id, deload_day, deload)
    assert manager.load_retained_session_context(deload)["phase"] == "deload"
    assert manager.load_deload_exercise_ids(as_of=return_day) == {
        int(manager.load_session_sets(deload).workout_exercise_id.iloc[0])
    }
    assert describe(recommendation(manager, plan, return_day)) == baseline

    other = workout_plan(manager, TrainingDay("Other", 0, (PRESS,)))
    manager.assign_scheduled_session(slot.day_id, deload_day, deload)
    assert manager.delete_training_plan(plan.plan_id)
    outcome = recommendation(manager, other, return_day)
    assert outcome.evidence_session_ids == (ordinary,)
    assert [goal.weight for goal in outcome.goals] == [60] * 3
    assert manager.load_sessions().session_id.nunique() == 2
    assert manager.load_retained_session_context(ordinary)["phase"] == "normal"
    assert manager.load_retained_session_context(deload)["phase"] == "deload"

    # Correct the mistaken deload assignment to a slot in an ordinary cycle.
    corrected = revise(
        manager,
        other,
        START + timedelta(weeks=1),
        maximum=12,
        settings=ProgressionSettings(START, 8),
    )
    ordinary_slot = saved_slot(manager, corrected, deload_day)
    manager.assign_scheduled_session(ordinary_slot.day_id, deload_day, deload)
    item = recommendation(manager, corrected, return_day)
    assert describe(item) == (
        "increase_reps",
        "one_more_rep",
        (deload,),
        [(40, 11, 11), (40, 10, 10), (40, 10, 10)],
    )


def test_public_service_refuses_a_prepared_slot_replaced_by_a_plan_revision(manager):
    plan = workout_plan(manager, TrainingDay("Original", 0, (PRESS,)))
    source = record(manager, START, 1, plan=plan)
    day = START + timedelta(weeks=1)
    held = prepare(manager, plan, day)
    assert describe(manager.recommend_prepared_workout(held).exercises[0]) == (
        "increase_weight",
        "upper_range_confirmed",
        (source,),
        [(62.5, 8, 8)] * 3,
    )
    revised = revise(manager, plan, day)
    assert describe(
        manager.recommend_prepared_workout(prepare(manager, revised, day)).exercises[0]
    ) == ("maintain", "prescription_changed", (source,), [(60, 6, 8)] * 3)
    with pytest.raises(ValueError, match="Prepare|refresh|again"):
        manager.recommend_prepared_workout(held)


def test_public_service_refreshes_a_prepared_slot_after_link_and_unlink(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    day = START + timedelta(weeks=1)
    source = record(manager, START, 1, plan=plan)
    held = prepare(manager, plan, day)
    before = ("increase_weight", "upper_range_confirmed", (source,), [(62.5, 8, 8)] * 3)
    assert describe(manager.recommend_prepared_workout(held).exercises[0]) == before
    session = record(manager, day, 1, (9, 9, 9), plan=plan)
    assert describe(manager.recommend_prepared_workout(held).exercises[0]) == (
        "insufficient_data",
        "already_recorded",
        (),
        [],
    )
    assert manager.recommend_prepared_workout(held) == manager.recommend_prepared_workout(
        prepare(manager, plan, day)
    )
    slot = saved_slot(manager, plan, day)
    manager.unassign_scheduled_session(slot.day_id, day, session)
    assert describe(manager.recommend_prepared_workout(held).exercises[0]) == (
        "increase_reps",
        "one_more_rep",
        (session,),
        [(60, 10, 10), (60, 9, 9), (60, 9, 9)],
    )


def test_legacy_unlinked_comparable_performance_without_invented_compliance(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    session = record(manager, START, 1)
    day = START + timedelta(weeks=1)
    item = recommendation(manager, plan, day)
    assert describe(item) == (
        "increase_weight",
        "upper_range_confirmed",
        (session,),
        [(62.5, 8, 8)] * 3,
    )
    assert any(
        "prescription" in notice.lower() and "unknown" in notice.lower() for notice in item.notices
    )

    revised = revise(manager, plan, day, step=5)
    item = recommendation(manager, revised, day)
    assert describe(item) == ("maintain", "unknown_prescription", (session,), [(60, 6, 8)] * 3)
    readings = load_exercise_starting_history(manager.engine, {1}, as_of=day)[1]
    assert readings[0]["prescription"] is None and readings[0]["training_phase"] == "unknown"
    recorded = record(manager, day, 1, (8, 8, 8))
    item = recommendation(manager, revised, day + timedelta(weeks=1))
    assert describe(item) == (
        "increase_weight",
        "upper_range_confirmed",
        (recorded,),
        [(65, 6, 6)] * 3,
    )


def test_held_recommendation_uses_import_corrections_relink_and_deletion(manager, upload_ui):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    older = record(manager, START, 1, plan=plan)
    import_day = START + timedelta(days=8)
    slot_day = START + timedelta(days=7)
    next_day = START + timedelta(days=14)
    with read_scope():
        held = prepare(manager, plan, next_day)

        def evaluate():
            return describe(manager.recommend_prepared_workout(held).exercises[0])

        assert evaluate() == (
            "increase_weight",
            "upper_range_confirmed",
            (older,),
            [(62.5, 8, 8)] * 3,
        )
        upload = SidebarUpload(manager=manager, sidebar=True)
        parsed = upload._parse_txt(
            "1. Audit Press\nResult: working: 10x60 / 9x60 / 8x60\nRIR: 2 / 2 / 2"
        )
        upload._process(
            upload._review_loads(parsed, import_day, "test"), import_day, time(9), time(10)
        )
        imported = int(manager.load_sessions().session_id.max())
        unchanged = (
            "increase_reps",
            "one_more_rep",
            (imported,),
            [(60, 11, 11), (60, 9, 9), (60, 8, 8)],
        )
        assert evaluate() == unchanged
        slot = saved_slot(manager, plan, slot_day)
        manager.assign_scheduled_session(slot.day_id, slot_day, imported)
        assert evaluate() == unchanged
        ids = manager.load_session_sets(imported).set_id.astype(int).tolist()
        manager.save_set_classifications(imported, {ids[-1]: True})
        manager.save_session_set_loads(imported, {ids[0]: SetLoad("external", 62.5)})
        partial = (
            "maintain",
            "incomplete_sets",
            (imported,),
            [(62.5, 10, 10), (60, 9, 9), (None, 8, 12)],
        )
        assert evaluate() == partial
        manager.unassign_scheduled_session(slot.day_id, slot_day, imported)
        assert evaluate() == partial
        alternate_day = START + timedelta(days=9)
        another = workout_plan(manager, TrainingDay("Other", 2, (PRESS,)))
        alternate = saved_slot(manager, another, alternate_day)
        manager.assign_scheduled_session(alternate.day_id, alternate_day, imported)
        assert evaluate() == partial
        assert manager.delete_session(imported)
        assert evaluate() == (
            "increase_weight",
            "upper_range_confirmed",
            (older,),
            [(62.5, 8, 8)] * 3,
        )
        with manager.engine.connect() as connection:
            assert (
                connection.execute(
                    select(provenance.c.session_id).where(provenance.c.session_id == imported)
                ).first()
                is None
            )
        assert manager.delete_training_plan(plan.plan_id)
        with pytest.raises(ValueError, match="Prepare the workout again"):
            evaluate()


def test_rollback_and_other_render_commit_refresh_authoritative_inputs(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    source = record(manager, START, 1, plan=plan)
    day = START + timedelta(weeks=1)
    set_id = int(manager.load_session_sets(source).set_id.iloc[-1])
    with read_scope():
        held = prepare(manager, plan, day)
        before = manager.recommend_prepared_workout(held)
        assert before.exercises[0].reason_code == "upper_range_confirmed"
        with manager.engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(classifications.insert().values(set_id=set_id, is_warmup=True))
            reader = DataManager(engine=ConnectionScope(connection))
            assert (
                reader.recommend_prepared_workout(held).exercises[0].reason_code
                == "incomplete_sets"
            )
            transaction.rollback()
        assert manager.recommend_prepared_workout(held) == before
        # Same engine, distinct render context. A completed application write invalidates both.
        with ThreadPoolExecutor(max_workers=1) as thread:
            thread.submit(manager.save_set_classifications, source, {set_id: True}).result()
        item = manager.recommend_prepared_workout(held).exercises[0]
        assert describe(item) == (
            "maintain",
            "incomplete_sets",
            (source,),
            [(60, 12, 12), (60, 12, 12), (None, 8, 12)],
        )


def test_retained_match_disambiguates_only_its_own_position(manager):
    primary = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    other = workout_plan(manager, TrainingDay("Other press", 0, (PRESS,)))
    source = record(manager, START, 1, plan=primary)
    assert record(manager, START, 1, (9, 9, 9)) == source
    slot = saved_slot(manager, primary, START)
    target = prepare(manager, primary, START).upcoming.targets[0].plan_exercise_id
    entry = int(manager.load_workout_exercises().workout_exercise_id.max())
    manager.save_exercise_match(source, target, entry)
    day = START + timedelta(weeks=1)
    held = prepare(manager, primary, day)
    local = ("increase_reps", "one_more_rep", (source,), [(60, 10, 10), (60, 9, 9), (60, 9, 9)])
    assert describe(manager.recommend_prepared_workout(held).exercises[0]) == local
    manager.remove_exercise_match(source, target)
    assert (
        manager.recommend_prepared_workout(held).exercises[0].reason_code
        == "ambiguous_recorded_exercises"
    )
    manager.save_exercise_match(source, target, entry)
    manager.unassign_scheduled_session(slot.day_id, START, source)
    assert describe(recommendation(manager, primary, day)) == local
    assert describe(recommendation(manager, other, day)) == (
        "insufficient_data",
        "ambiguous_recorded_exercises",
        (source,),
        [],
    )


def test_retained_replacement_prescription_belongs_to_actual_exercise(manager):
    primary = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    other = workout_plan(
        manager,
        TrainingDay("Rows", 0, (replace(PRESS, exercise_id=3, target_min=6, target_max=8),)),
    )
    source = record(manager, START, 3, plan=primary)
    slot = saved_slot(manager, primary, START)
    target = prepare(manager, primary, START).upcoming.targets[0].plan_exercise_id
    entry = int(manager.load_workout_exercises().workout_exercise_id.max())
    manager.save_exercise_match(source, target, entry)
    day = START + timedelta(weeks=1)
    expected = ("maintain", "prescription_changed", (source,), [(60, 6, 8)] * 3)
    assert describe(recommendation(manager, other, day)) == expected
    assert recommendation(manager, primary, day).reason_code == "no_history"
    manager.unassign_scheduled_session(slot.day_id, START, source)
    assert describe(recommendation(manager, other, day)) == expected
    assert recommendation(manager, primary, day).reason_code == "no_history"


def test_unlinking_a_relevant_omission_does_not_unlock_an_older_success(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    other = workout_plan(manager, TrainingDay("Other", 0, (PRESS,)))
    older = record(manager, START, 1, plan=plan)
    omitted_day = START + timedelta(weeks=1)
    omitted = record(manager, omitted_day, 3, plan=plan)
    upcoming = omitted_day + timedelta(weeks=1)
    expected = ("insufficient_data", "incomplete_sets", (omitted,), [])
    assert describe(recommendation(manager, plan, upcoming)) == expected
    slot = saved_slot(manager, plan, omitted_day)
    manager.unassign_scheduled_session(slot.day_id, omitted_day, omitted)
    assert saved_slot(manager, plan, omitted_day).session_id is None
    assert describe(recommendation(manager, plan, upcoming)) == expected
    assert describe(recommendation(manager, other, upcoming)) == (
        "increase_weight",
        "upper_range_confirmed",
        (older,),
        [(62.5, 8, 8)] * 3,
    )
    assert manager.clear_retained_session_context(omitted)
    assert describe(recommendation(manager, plan, upcoming)) == (
        "increase_weight",
        "upper_range_confirmed",
        (older,),
        [(62.5, 8, 8)] * 3,
    )


def test_new_plan_does_not_inherit_deleted_calendar_or_retained_omission(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    older = record(manager, START, 1, plan=plan)
    omitted_day = START + timedelta(weeks=1)
    record(manager, omitted_day, 3, plan=plan)
    upcoming = omitted_day + timedelta(weeks=1)
    held = prepare(manager, plan, upcoming)
    assert manager.delete_training_plan(plan.plan_id)
    recreated = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    assert describe(recommendation(manager, recreated, upcoming)) == (
        "increase_weight",
        "upper_range_confirmed",
        (older,),
        [(62.5, 8, 8)] * 3,
    )
    with pytest.raises(ValueError, match="Prepare the workout again"):
        manager.recommend_prepared_workout(held)


def test_new_identical_plan_is_not_the_old_prepared_occurrence(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    held = prepare(manager, plan, START)
    assert manager.delete_training_plan(plan.plan_id)
    recreated = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    assert recommendation(manager, recreated, START).reason_code == "no_history"
    with pytest.raises(ValueError, match="Prepare the workout again"):
        manager.recommend_prepared_workout(held)


def test_manual_start_defaults_refresh_when_reusing_prepared_selection(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    with read_scope():
        held = prepare(manager, plan, START)
        result = manager.recommend_prepared_workout(held)
        item = result.exercises[0]
        assert item.reason_code == "no_history"
        assert manager.load_starting_loads(held.upcoming, item, result.block) == ()
        goals = tuple(
            SetGoal(weight, 8, 12, "reps", load_type="external") for weight in (50, 50, 45)
        )
        manager.save_starting_loads(held.upcoming, item, result.block, goals)
        current = manager.recommend_prepared_workout(held)
        assert current.exercises[0].reason_code == "no_history"
        restored = manager.load_starting_loads(held.upcoming, current.exercises[0], current.block)
        assert [(g.weight, g.minimum, g.maximum) for g in restored] == [
            (50, 8, 12),
            (50, 8, 12),
            (45, 8, 12),
        ]


def test_link_dialog_reports_and_explicitly_clears_incorrect_retained_context(manager):
    plan = workout_plan(manager, TrainingDay("Wrong source", 0, (PRESS,)))
    source = record(manager, START, 1, plan=plan)
    slot = saved_slot(manager, plan, START)
    app = AppTest.from_string("""
from datetime import date
import streamlit as st
from ui.session_plan_link_view import _render_link_dialog
_render_link_dialog(st.session_state['manager'], st.session_state['session'], date(2026, 5, 4))
""")
    app.session_state["manager"] = manager
    app.session_state["session"] = source
    app.run()
    app.button(key=f"history_link_{source}_unlink").click().run()
    assert not app.exception
    assert any("Retained training context" in msg.value for msg in app.info)
    assert app.button(key=f"history_link_{source}_clear").disabled
    app.checkbox(key=f"history_link_{source}_confirm_clear").check().run()
    app.button(key=f"history_link_{source}_clear").click().run()
    assert not app.exception
    assert manager.load_retained_session_context(source) is None
    assert manager.load_session_plan_assignments((source,)) == {}
    assert manager.load_session_sets(source).repetitions.tolist() == [12, 12, 12]
    manager.assign_scheduled_session(slot.day_id, START, source)
    with pytest.raises(ValueError, match="Relink"):
        manager.clear_retained_session_context(source)


def test_upgrade_backfills_links_only_and_rolls_back_on_error(fresh_engine, monkeypatch):
    from db import session_provenance

    prior = MIGRATIONS[:-1]
    with monkeypatch.context() as legacy:
        legacy.setattr("db.migrate.MIGRATIONS", prior)
        bootstrap_database(fresh_engine)
    with fresh_engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO exercises(exercise_name) VALUES ('Audit Press'), ('Audit Row')"
        )
    manager = DataManager(engine=fresh_engine)
    plan = phased_plan(manager)
    day = START + timedelta(weeks=5)
    linked = record(manager, day, 2, plan=plan)
    target = prepare(manager, plan, day).upcoming.targets[0].plan_exercise_id
    entry = int(manager.load_workout_exercises().workout_exercise_id.max())
    manager.save_exercise_match(linked, target, entry)
    unlinked = record(manager, day + timedelta(days=1), 1)
    before = manager.load_plan_session_links()
    sets_before = manager.load_sets_raw()
    original = session_provenance.preserve_session_provenance

    def fail_after_backfill(connection):
        original(connection)
        raise RuntimeError("abort after backfill")

    with monkeypatch.context() as failed:
        failed.setattr(session_provenance, "preserve_session_provenance", fail_after_backfill)
        with pytest.raises(RuntimeError, match="abort after backfill"):
            migrate(fresh_engine, apply=True)
    assert not inspect(fresh_engine).has_table(provenance.name)
    revision = MIGRATIONS[-1].REVISION
    assert migrate(fresh_engine, apply=True) == [revision]
    assert migrate(fresh_engine, apply=True) == []
    with fresh_engine.connect() as connection:
        snapshots = connection.execute(select(provenance)).mappings().all()
    assert [(row["session_id"], row["phase"]) for row in snapshots] == [(linked, "deload")]
    assert snapshots[0]["targets"][0]["target_min"] == 6
    assert snapshots[0]["targets"][0]["workout_exercise_id"] == entry
    assert unlinked != linked and manager.load_plan_session_links() == before
    assert manager.load_sets_raw().equals(sets_before)
    outcome = recommendation(manager, plan, day + timedelta(weeks=1))
    assert describe(outcome) == ("maintain", "resume_after_deload", (unlinked,), [(60, 12, 12)] * 3)
