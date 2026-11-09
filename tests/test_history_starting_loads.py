"""Plan changes read real exercise history before offering manual settings."""

from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from db.exercise_history_load_settings import (
    confirm_legacy_body_mass_history,
    load_legacy_body_mass_exercise_ids,
)
from db.exercise_starting_history import load_exercise_starting_history
from db.plan_adherence import actual_exercises, actual_sets, catalog_exercises
from db.plan_schedule import assign_scheduled_session, links, load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.set_loads import insert_set_load
from db.training_plans import save_training_plan
from models.set_load import SetLoad
from models.training_plan import ProgressionSettings
from test_manual_start import seed_without_records
from test_next_workout_view import AS_OF, exercise_html, seed, start_app
from test_plan_schedule import schedule_data as schedule_data
from test_progression import PLAN


def first_recommendation(engine, plan, *, as_of=AS_OF):
    slot = next(
        s
        for s in load_scheduled_workouts(engine, plan.plan_id, as_of, as_of + timedelta(days=14))
        if s.session_id is None
    )
    return load_workout_recommendations(
        engine, plan.plan_id, slot.day_id, slot.scheduled_date, as_of=as_of
    )


def log(engine, sessions, sid, day, weights, *, exercise_id=1, rir=2, warmup=False, load=None):
    with engine.begin() as connection:
        exists = connection.execute(
            select(sessions.c.session_id).where(sessions.c.session_id == sid)
        ).first()
        if exists:
            connection.execute(
                sessions.update().where(sessions.c.session_id == sid).values(session_date=day)
            )
        else:
            connection.execute(sessions.insert().values(session_id=sid, session_date=day))
        connection.execute(
            actual_exercises.insert().values(
                workout_exercise_id=sid * 100, session_id=sid, exercise_id=exercise_id
            )
        )
        from db.set_classifications import classifications

        for index, weight in enumerate(weights, 1):
            set_id = connection.execute(
                actual_sets.insert().values(
                    workout_exercise_id=sid * 100,
                    set_number=index,
                    weight=weight,
                    repetitions=10,
                    rir=rir,
                )
            ).inserted_primary_key[0]
            if warmup:
                connection.execute(classifications.insert().values(set_id=set_id, is_warmup=True))
            if load is not None:
                insert_set_load(connection, set_id, load)


@pytest.mark.parametrize(
    "change", ["new_plan", "rir", "range", "more_sets", "fewer_sets", "order", "new_block"]
)
def test_plan_changes_automatically_reuse_recorded_loads_without_an_increase(
    schedule_data, monkeypatch, change
):
    monkeypatch.setattr("db.training_plans.date", SimpleNamespace(today=lambda: AS_OF))
    engine, _, _, _ = schedule_data
    old = seed(schedule_data)
    planned = old.draft.days[0].exercises[0]
    if change == "rir":
        planned = replace(planned, target_rir=3)
    elif change == "range":
        planned = replace(planned, target_min=8, target_max=12)
    elif change in ("more_sets", "fewer_sets"):
        planned = replace(planned, set_count=5 if change == "more_sets" else 2)
    exercises = (planned,)
    if change == "order":
        with engine.begin() as connection:
            connection.execute(
                catalog_exercises.insert().values(exercise_id=2, exercise_name="Other exercise")
            )
        exercises = (replace(PLAN, exercise_id=2), planned)
    new = save_training_plan(
        engine,
        replace(
            old.draft,
            effective_from=AS_OF,
            days=(replace(old.draft.days[0], name="Revised workout", exercises=exercises),),
            progression=ProgressionSettings(AS_OF, 7)
            if change == "new_block"
            else old.draft.progression,
        ),
        plan_id=None if change == "new_plan" else old.plan_id,
    )
    with engine.connect() as connection:
        before = (
            connection.execute(select(actual_sets)).all(),
            connection.execute(select(links)).all(),
        )
    item = next(i for i in first_recommendation(engine, new).exercises if i.actual_exercise_id == 1)
    assert (item.action, item.reason_code) == ("maintain", "reuse_exercise_baseline")
    assert [g.weight for g in item.goals] == [60.0] * planned.set_count
    assert all(
        (g.minimum, g.maximum) == (planned.target_min, planned.target_max) for g in item.goals
    )
    assert item.target_rir == planned.target_rir
    assert item.evidence_session_ids == (3,)
    assert item.evidence_dates == (date(2026, 5, 18),)
    with engine.connect() as connection:
        assert before == (
            connection.execute(select(actual_sets)).all(),
            connection.execute(select(links)).all(),
        )


def test_new_history_overrides_saved_manual_choices_and_then_drives_progression(schedule_data):
    engine, _, source, sessions = schedule_data
    plan = seed_without_records(engine, source)
    app = start_app(engine, plan)
    for field in app.number_input:
        field.set_value(55.0)
    app.run()
    assert "Saved starting loads" in exercise_html(app)
    log(engine, sessions, 2, date(2026, 5, 18), (60.0, 55.0, 50.0))
    app.run()
    assert "Saved starting loads" not in exercise_html(app)
    assert "Starting loads read automatically" in exercise_html(app)
    assert not [n for n in app.number_input if n.key.startswith("manual_start_")]
    item = first_recommendation(engine, plan).exercises[0]
    assert [g.weight for g in item.goals] == [60.0, 55.0, 50.0]
    slot = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 2)
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "equalize_loads"
    assert [g.weight for g in item.goals] == [60.0, 60.0, 55.0]


def test_latest_usable_unlinked_history_wins_over_future_and_warmup_only_records(schedule_data):
    engine, _, source, sessions = schedule_data
    plan = seed_without_records(engine, source)
    log(engine, sessions, 2, date(2026, 5, 17), (60.0, 55.0, 50.0))
    log(engine, sessions, 3, date(2026, 5, 18), (20.0,) * 3, warmup=True)
    log(engine, sessions, 4, date(2026, 5, 21), (100.0,) * 3)
    item = first_recommendation(engine, plan).exercises[0]
    assert [g.weight for g in item.goals] == [60.0, 55.0, 50.0]
    assert item.evidence_session_ids == (2,)
    assert all(
        record["session_id"] != 4
        for record in load_exercise_starting_history(engine, {1}, as_of=AS_OF)[1]
    )


def test_later_heavy_trials_do_not_replace_the_first_working_start(schedule_data):
    engine, _, source, sessions = schedule_data
    plan = seed_without_records(engine, source)
    log(engine, sessions, 2, date(2026, 5, 18), (40.0, 50.0, 55.0))
    item = first_recommendation(engine, plan).exercises[0]
    assert [g.weight for g in item.goals] == [40.0] * 3
    assert any("first recorded working load" in notice for notice in item.notices)


@pytest.mark.parametrize(
    "load", [SetLoad("bodyweight", 5.0, 80.0), SetLoad("assisted_bodyweight", 0.0, 80.0, 20.0)]
)
def test_explicit_bodyweight_settings_are_reused_without_future_body_mass(schedule_data, load):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(
            catalog_exercises.update()
            .where(catalog_exercises.c.exercise_id == 1)
            .values(
                exercise_name="Assisted Pull-Up"
                if load.load_type == "assisted_bodyweight"
                else "Pull-Up"
            )
        )
    plan = seed_without_records(engine, source)
    log(engine, sessions, 2, date(2026, 5, 18), (load.external_weight_kg,) * 3, load=load)
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "reuse_exercise_baseline"
    assert all(
        g.weight == load.external_weight_kg
        and g.load_type == load.load_type
        and g.assistance_kg == load.assistance_kg
        for g in item.goals
    )


def test_old_plan_deload_is_excluded_from_new_plan_starting_history(schedule_data):
    engine, _, _, sessions = schedule_data
    old = seed(schedule_data)
    deload = date(2026, 6, 15)
    log(engine, sessions, 1, deload, (40.0,) * 3)
    slot = load_scheduled_workouts(engine, old.plan_id, deload, deload)[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 1)
    start = date(2026, 6, 22)
    new = save_training_plan(
        engine, replace(old.draft, effective_from=start, progression=ProgressionSettings(start, 7))
    )
    item = first_recommendation(engine, new, as_of=start).exercises[0]
    assert item.reason_code == "reuse_exercise_baseline"
    assert [g.weight for g in item.goals] == [60.0] * 3
    assert item.evidence_session_ids == (3,)
    assert any("older history" in notice for notice in item.notices)


def test_confirmed_legacy_body_mass_supplies_zero_additional_load_and_preserves_old_weights(
    schedule_data,
):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(
            catalog_exercises.update()
            .where(catalog_exercises.c.exercise_id == 1)
            .values(exercise_name="Pronated-Grip Pull-Up")
        )
    plan = seed_without_records(engine, source)
    log(engine, sessions, 2, date(2026, 5, 18), (90.3,) * 3)
    assert not first_recommendation(engine, plan).exercises[0].goals
    confirm_legacy_body_mass_history(engine, 1)
    assert load_legacy_body_mass_exercise_ids(engine) == frozenset({1})
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "reuse_exercise_baseline"
    assert all(g.weight == 0.0 and g.load_type == "bodyweight" for g in item.goals)
    app = start_app(engine, plan)
    assert not [n for n in app.number_input if n.key.startswith("manual_start_")]
    slot = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 2)
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "bodyweight_load_manual"
    assert all(g.weight == 0.0 and g.load_type == "bodyweight" for g in item.goals)
    with engine.connect() as connection:
        assert connection.execute(select(actual_sets.c.weight)).scalars().all() == [90.3] * 3
    confirm_legacy_body_mass_history(engine, 1, confirmed=False)
    assert not load_legacy_body_mass_exercise_ids(engine)


def test_confirmed_legacy_meaning_does_not_override_explicit_added_weight(schedule_data):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(
            catalog_exercises.update()
            .where(catalog_exercises.c.exercise_id == 1)
            .values(exercise_name="Pronated-Grip Pull-Up")
        )
    plan = seed_without_records(engine, source)
    confirm_legacy_body_mass_history(engine, 1)
    log(engine, sessions, 2, date(2026, 5, 18), (5.0,) * 3, load=SetLoad("bodyweight", 5.0, 80.0))
    item = first_recommendation(engine, plan).exercises[0]
    assert all(g.weight == 5.0 and g.load_type == "bodyweight" for g in item.goals)


def test_history_from_another_exercise_never_silently_becomes_a_starting_load(schedule_data):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(
            catalog_exercises.insert().values(exercise_id=2, exercise_name="Different exercise")
        )
    plan = seed_without_records(engine, source)
    log(engine, sessions, 2, date(2026, 5, 18), (100.0,) * 3, exercise_id=2)
    item = first_recommendation(engine, plan).exercises[0]
    assert item.actual_exercise_id == 1 and not item.goals


def test_timed_history_supplies_loads_using_the_current_time_range(schedule_data):
    engine, _, source, sessions = schedule_data
    planned = replace(PLAN, target_unit="seconds", target_min=30, target_max=60, target_rir=None)
    plan = save_training_plan(
        engine,
        replace(
            source.draft,
            effective_from=date(2026, 5, 4),
            days=(replace(source.draft.days[0], exercises=(planned,)),),
            progression=ProgressionSettings(date(2026, 5, 4), 7),
        ),
    )
    log(engine, sessions, 2, date(2026, 5, 18), (0.0,) * 3, rir=None)
    with engine.begin() as connection:
        connection.execute(actual_sets.update().values(duration_seconds=35, repetitions=0))
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "reuse_exercise_baseline"
    assert all(
        g.weight == 0.0 and g.minimum == 30 and g.maximum == 60 and g.unit == "seconds"
        for g in item.goals
    )
    assert item.target_rir is None


def test_zero_load_hang_history_needs_no_body_mass_confirmation(schedule_data):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(
            catalog_exercises.update()
            .where(catalog_exercises.c.exercise_id == 1)
            .values(exercise_name="Dead hang")
        )
    planned = replace(
        PLAN, set_count=1, target_unit="seconds", target_min=30, target_max=60, target_rir=None
    )
    plan = save_training_plan(
        engine,
        replace(
            source.draft,
            effective_from=date(2026, 5, 4),
            days=(replace(source.draft.days[0], exercises=(planned,)),),
            progression=ProgressionSettings(date(2026, 5, 4), 7),
        ),
    )
    log(engine, sessions, 2, date(2026, 5, 18), (0.0,), rir=None)
    with engine.begin() as connection:
        connection.execute(actual_sets.update().values(duration_seconds=35, repetitions=0))
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "reuse_exercise_baseline"
    assert all(g.weight == 0 and g.load_type == "bodyweight" for g in item.goals)
    slot = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 2)
    item = first_recommendation(engine, plan).exercises[0]
    assert item.reason_code == "more_time"
    assert item.goals[0].weight == 0 and item.goals[0].minimum == 40
