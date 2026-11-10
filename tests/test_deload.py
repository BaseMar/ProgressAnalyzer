"""Deload boundaries, supported equipment loads, return baselines and analytics."""

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from db.plan_adherence import actual_exercises, actual_sets, load_plan_performance
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.set_classifications import classifications
from db.training_plans import load_training_plan_version, save_training_plan
from metrics.plan_adherence import compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.progression import recommend_workout
from metrics.training_block import deload_adjusted_input, training_block_phase
from models.progression import DeloadPolicy
from models.training_plan import ProgressionSettings
from test_plan_performance import data
from test_plan_schedule import schedule_data as schedule_data
from test_progression import PLAN, upcoming, working
from ui.utils.plan_charts import exercise_history_chart

START = date(2026, 5, 4)
SETTINGS = ProgressionSettings(START, 7)
DELOAD = date(2026, 6, 15)
RETURN = date(2026, 6, 22)


def recommend(*entries, day=DELOAD, as_of=None, planned=PLAN, settings=SETTINGS, **options):
    return recommend_workout(
        data(*entries), upcoming(planned, day=day), as_of=as_of or day, settings=settings, **options
    )


@pytest.mark.parametrize("weeks", [6, 7, 8])
def test_phase_boundaries_and_automatic_repetition(weeks):
    settings = ProgressionSettings(START, weeks)
    length = timedelta(weeks=weeks)
    deload = START + length - timedelta(days=7)
    assert training_block_phase(START - timedelta(days=1), settings).phase == "not_started"
    first = training_block_phase(START, settings)
    assert (first.phase, first.cycle, first.week, first.cycle_start) == ("normal", 1, 1, START)
    assert first.cycle_end == START + length - timedelta(days=1)
    assert first.deload_start == deload
    assert training_block_phase(deload - timedelta(days=1), settings).phase == "normal"
    assert training_block_phase(deload, settings).phase == "deload"
    assert training_block_phase(START + length - timedelta(days=1), settings).phase == "deload"
    second = training_block_phase(START + length, settings)
    assert (second.phase, second.cycle, second.week) == ("normal", 2, 1)
    assert training_block_phase(deload + length * 2, settings).cycle == 3


def test_midweek_anchor_and_unconfigured_phase_are_explicit():
    settings = ProgressionSettings(START + timedelta(days=2), 6)
    assert training_block_phase(settings.block_start + timedelta(days=6), settings).week == 1
    assert training_block_phase(settings.block_start + timedelta(days=7), settings).week == 2
    assert training_block_phase(START, None).phase == "unconfigured"
    with pytest.raises(ValueError, match="must be a date"):
        training_block_phase(datetime.now(), settings)


@pytest.mark.parametrize(
    "values",
    [
        {"retained_set_fraction": 0},
        {"retained_set_fraction": True},
        {"load_reduction": float("nan")},
        {"load_reduction": 0.3, "max_load_reduction": 0.2},
        {"minimum_rir": None},
        {"extra_rir": 0},
    ],
)
def test_invalid_deload_policies_are_rejected(values):
    with pytest.raises(ValueError):
        DeloadPolicy(**values)


def test_deload_keeps_sets_reps_and_reduces_only_load_without_writing_evidence():
    first, last = (
        working(1, date(2026, 6, 1), (10, 10, 10)),
        working(2, date(2026, 6, 8), (10, 10, 10)),
    )
    result = recommend(first, last)
    item = result.exercises[0]
    assert result.block.phase == "deload"
    assert (item.action, item.reason_code, item.target_rir) == ("deload", "scheduled_deload", 3)
    assert item.target_rir_max == 4
    assert [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals] == [
        (40.0, 10, 10)
    ] * 3
    assert item.evidence_session_ids == (2,)
    assert last[1].sets[0].weight == 60.0
    assert last[0].targets[0].exercise.set_count == 3


@pytest.mark.parametrize("count, expected", [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])
def test_deload_preserves_every_planned_set(count, expected):
    planned = replace(PLAN, set_count=count)
    result = recommend(
        working(1, date(2026, 6, 8), (8,) * count, planned=planned), planned=planned
    ).exercises[0]
    assert len(result.goals) == expected


def test_deload_uses_the_selected_rir_band():
    planned = replace(PLAN, target_rir=5)
    result = recommend(
        working(1, date(2026, 6, 8), rir=5, planned=planned), planned=planned
    ).exercises[0]
    assert (result.target_rir, result.target_rir_max) == (3, 4)


def test_policy_can_change_reduction_and_preserve_decimal_equipment_steps():
    planned = replace(PLAN, weight_increment=0.2)
    result = recommend(
        working(1, date(2026, 6, 8), planned=planned, weight=12.1),
        planned=planned,
        deload_policy=DeloadPolicy(retained_set_fraction=0.75),
    ).exercises[0]
    assert len(result.goals) == 3
    assert result.goals[0].weight == 8.3


@pytest.mark.parametrize(
    "problem, code",
    [
        ("missing_step", "missing_weight_step"),
        ("large_step", "deload_load_not_supported"),
        ("zero_load", "deload_load_not_supported"),
        ("partial", "incomplete_sets"),
        ("missing_rir", "missing_rir"),
        ("missing_target", "missing_target_rir"),
    ],
)
def test_deload_does_not_invent_loads_or_use_incomplete_data(problem, code):
    planned = replace(
        PLAN,
        weight_increment=None
        if problem == "missing_step"
        else 20.0
        if problem == "large_step"
        else 2.5,
        target_rir=None if problem == "missing_target" else 2,
    )
    if problem == "large_step":
        planned = replace(planned, weight_increment=25.0)
    entry = working(
        1,
        date(2026, 6, 8),
        (8, 8) if problem == "partial" else (8, 8, 8),
        weight=0.0 if problem == "zero_load" else 60.0,
        rir=None if problem == "missing_rir" else 2,
        planned=planned,
    )
    result = recommend(entry, planned=planned).exercises[0]
    assert (result.action, result.reason_code, result.goals) == ("insufficient_data", code, ())


def test_deload_uses_mixed_loads_individually_and_never_rounds_to_zero():
    entry = working(1, date(2026, 6, 8))
    entry = (
        entry[0],
        replace(
            entry[1],
            sets=(entry[1].sets[0], replace(entry[1].sets[1], weight=65.0), entry[1].sets[2]),
        ),
        entry[2],
    )
    assert [item.weight for item in recommend(entry).exercises[0].goals] == [40.0, 45.0, 40.0]
    assert not recommend(working(1, date(2026, 6, 8), weight=2.5)).exercises[0].goals


def test_substitute_has_separate_baseline_and_requires_its_own_equipment_step():
    entry = working(1, date(2026, 6, 8), actual_id=2)
    assert recommend(entry).exercises[0].reason_code == "no_normal_baseline"
    assert (
        recommend(entry, substitutions={101: 2}).exercises[0].reason_code == "missing_weight_step"
    )
    item = recommend(entry, substitutions={101: 2}, replacement_weight_steps={2: 5.0}).exercises[0]
    assert item.actual_exercise_id == 2
    assert item.goals[0].weight == 40.0


def test_deload_is_not_its_own_baseline_even_after_another_deload_session():
    normal = working(1, date(2026, 6, 8), (10, 10, 10))
    lighter = working(2, DELOAD, (6, 6), weight=52.5, rir=4)
    assert recommend(normal, lighter).exercises[0].evidence_session_ids == (1,)
    assert recommend(lighter).exercises[0].reason_code == "no_normal_baseline"


def test_latest_empty_execution_blocks_older_success_and_future_work_is_ignored():
    normal = working(1, date(2026, 6, 1), (10, 10, 10))
    empty = working(2, date(2026, 6, 8), ())
    assert recommend(normal, empty).exercises[0].reason_code == "incomplete_sets"
    future = working(3, date(2026, 6, 8), (10, 10, 10), weight=100.0)
    future = (
        replace(future[0], slot=replace(future[0].slot, performed_on=DELOAD + timedelta(days=1))),
        future[1],
        future[2],
    )
    assert recommend(normal, future).exercises[0].evidence_session_ids == (1,)


def test_return_uses_last_normal_load_without_increase_or_deload_confirmation():
    entries = (
        working(1, date(2026, 6, 1), (10, 10, 10)),
        working(2, date(2026, 6, 8), (10, 10, 10)),
        working(3, DELOAD, (6, 6), weight=52.5, rir=4),
    )
    item = recommend(*entries, day=RETURN).exercises[0]
    assert (item.action, item.reason_code) == ("maintain", "resume_after_deload")
    assert [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals] == [(60.0, 6, 10)] * 3
    assert item.evidence_session_ids == (2,)


def test_return_needs_no_weight_increment_and_does_not_fall_back_past_partial_latest():
    planned = replace(PLAN, weight_increment=None)
    entry = working(1, date(2026, 6, 8), (10, 10, 10), planned=planned)
    assert (
        recommend(entry, day=RETURN, planned=planned).exercises[0].reason_code
        == "resume_after_deload"
    )
    partial = working(2, date(2026, 6, 8), (10, 10), planned=planned)
    assert (
        recommend(entry, partial, day=RETURN, planned=planned).exercises[0].reason_code
        == "incomplete_sets"
    )


def test_post_deload_confirmations_restart_in_new_cycle():
    old = working(1, date(2026, 6, 8), (10, 10, 10))
    first = working(2, RETURN, (10, 10, 10))
    second = working(3, RETURN + timedelta(days=7), (10, 10, 10))
    assert (
        recommend(old, first, day=RETURN + timedelta(days=7)).exercises[0].reason_code
        == "upper_range_confirmed"
    )
    assert (
        recommend(old, first, second, day=RETURN + timedelta(days=14)).exercises[0].action
        == "increase_weight"
    )


def test_normal_week_uses_existing_rep_rule_and_ignores_future_results():
    known = working(1, date(2026, 6, 1), (8, 8, 8))
    future = working(2, date(2026, 6, 8), (10, 10, 10))
    result = recommend(known, future, day=date(2026, 6, 8), as_of=date(2026, 6, 2)).exercises[0]
    assert result.action == "increase_reps"
    assert result.evidence_session_ids == (1,)


def test_long_gap_and_multiple_empty_cycles_do_not_reuse_stale_baselines():
    entry = working(1, date(2026, 6, 1))
    assert (
        recommend(entry, day=RETURN + timedelta(days=7)).exercises[0].reason_code == "history_gap"
    )
    assert (
        recommend(entry, day=RETURN + timedelta(weeks=7)).exercises[0].reason_code
        == "no_normal_baseline"
    )


def test_moved_deload_and_normal_done_in_deload_do_not_confirm_increases():
    normal = working(1, date(2026, 6, 8), (10, 10, 10))
    moved = working(2, DELOAD, (10, 10, 10))
    moved = (
        replace(moved[0], slot=replace(moved[0].slot, performed_on=RETURN)),
        moved[1],
        moved[2],
    )
    result = recommend(normal, moved, day=RETURN + timedelta(days=7)).exercises[0]
    assert result.reason_code == "resume_after_deload"
    assert result.evidence_session_ids == (1,)
    in_deload = (
        replace(normal[0], slot=replace(normal[0].slot, performed_on=DELOAD)),
        normal[1],
        normal[2],
    )
    assert recommend(in_deload, day=RETURN).exercises[0].reason_code == "no_normal_baseline"


def test_manual_block_reset_excludes_history_of_previous_settings():
    old = working(1, date(2026, 6, 8), (10, 10, 10))
    reset = ProgressionSettings(date(2026, 6, 1), 8)
    item = recommend(old, day=RETURN, settings=reset, settings_by_version={1: SETTINGS}).exercises[
        0
    ]
    assert item.reason_code == "no_normal_baseline"


@pytest.mark.parametrize(
    "day, logged, code",
    [
        (date(2026, 5, 18), date(2026, 5, 11), "one_more_rep"),
        (DELOAD, date(2026, 6, 8), "scheduled_deload"),
        (RETURN, date(2026, 6, 8), "resume_after_deload"),
    ],
)
def test_initial_block_setup_reuses_linked_unconfigured_version(day, logged, code):
    entry = working(1, logged, (8, 8, 8))
    snapshots = {1: None, 2: SETTINGS}
    target = upcoming(day=day)
    target = replace(target, slot=replace(target.slot, version_id=2))
    item = recommend_workout(
        data(entry), target, as_of=day, settings=SETTINGS, settings_by_version=snapshots
    ).exercises[0]
    assert item.reason_code == code
    assert item.evidence_session_ids == (1,)
    assert item.goals
    assert snapshots == {1: None, 2: SETTINGS}


@pytest.mark.parametrize(
    "scheduled, performed",
    [
        (START - timedelta(days=7), START - timedelta(days=7)),
        (START - timedelta(days=7), START),
        (START, START - timedelta(days=1)),
        (DELOAD, DELOAD),
        (date(2026, 6, 8), DELOAD),
        (DELOAD, RETURN),
    ],
)
def test_initial_block_setup_excludes_preblock_and_deload_history(scheduled, performed):
    entry = working(1, scheduled, (8, 8, 8))
    entry = (
        replace(entry[0], slot=replace(entry[0].slot, performed_on=performed)),
        entry[1],
        entry[2],
    )
    item = recommend(entry, day=RETURN, settings_by_version={1: None}).exercises[0]
    assert item.reason_code == "no_normal_baseline"
    assert not item.goals


def test_unconfigured_not_started_linked_and_past_slots_are_explicit():
    assert recommend(settings=None).block.phase == "unconfigured"
    assert (
        recommend(settings=ProgressionSettings(RETURN, 7)).exercises[0].reason_code
        == "before_block"
    )
    linked = upcoming(day=DELOAD)
    linked = replace(linked, slot=replace(linked.slot, session_id=7, performed_on=DELOAD))
    assert (
        recommend_workout(data(), linked, as_of=DELOAD, settings=SETTINGS).exercises[0].reason_code
        == "already_recorded"
    )
    with pytest.raises(ValueError, match="in the past"):
        recommend(as_of=RETURN)


def test_timed_deload_has_no_unsupported_numeric_prescription():
    planned = replace(PLAN, target_unit="seconds", target_min=30, target_max=60)
    item = recommend(
        working(1, date(2026, 6, 8), (60, 60, 60), planned=planned), planned=planned
    ).exercises[0]
    assert (item.action, item.reason_code, item.goals) == (
        "insufficient_data",
        "deload_timed_not_supported",
        (),
    )


def test_analytics_uses_reduced_targets_without_false_regression_or_missing_sets():
    entries = (
        working(1, date(2026, 6, 8), (10, 10, 10)),
        working(2, DELOAD, (10, 10, 10), weight=40.0, rir=3),
        working(3, RETURN, (10, 10, 10)),
    )
    source = data(*entries)
    rows = compute_plan_performance(source, as_of=RETURN, settings_by_version={1: SETTINGS})
    assert rows[1]["training_phase"] == "deload"
    assert rows[1]["missing_sets"] == 0
    assert (rows[1]["target_min"], rows[1]["target_max"], rows[1]["target_rir"]) == (6, 10, 3)
    assert rows[1]["reps_delta"] is None
    assert rows[1]["previous"] is None
    assert rows[2]["previous"]["session_id"] == 1
    assert rows[2]["reps_delta"] == 0
    report = compute_plan_adherence(deload_adjusted_input(source, {1: SETTINGS}), as_of=RETURN)
    assert report["summary"]["planned_sets"] == report["summary"]["covered_sets"] == 9
    assert report["summary"]["linked_workouts"] == 3
    assert source.workouts[1].targets[0].exercise.set_count == 3
    fig = exercise_history_chart(rows)
    assert list(fig.data[0].marker.symbol) == ["circle", "diamond", "circle"]
    assert (fig.layout.shapes[1].y0, fig.layout.shapes[1].y1) == (6, 10)


def test_future_performed_date_does_not_change_past_analytic_expectations():
    entry = working(1, date(2026, 6, 8))
    entry = (
        replace(entry[0], slot=replace(entry[0].slot, performed_on=DELOAD)),
        entry[1],
        entry[2],
    )
    adjusted = deload_adjusted_input(data(entry), {1: SETTINGS}, as_of=date(2026, 6, 10))
    assert adjusted.workouts[0].targets[0].exercise.set_count == 3


def test_readonly_service_uses_history_linked_before_initial_block_setup(schedule_data):
    engine, _, source, sessions = schedule_data
    next_day = date.today() + timedelta(days=(0 - date.today().weekday()) % 7)
    logged = next_day - timedelta(days=7)
    settings = ProgressionSettings(logged, 6)
    original = save_training_plan(
        engine,
        replace(
            source.draft,
            effective_from=logged,
            days=(replace(source.draft.days[0], exercises=(PLAN,)),),
            progression=None,
        ),
    )
    old_slot = load_scheduled_workouts(engine, original.plan_id, logged, logged)[0]
    with engine.begin() as connection:
        connection.execute(
            sessions.update().where(sessions.c.session_id == 2).values(session_date=logged)
        )
        connection.execute(
            actual_exercises.insert().values(workout_exercise_id=200, session_id=2, exercise_id=1)
        )
        connection.execute(
            actual_sets.insert(),
            [
                {
                    "set_id": 20 + number,
                    "workout_exercise_id": 200,
                    "set_number": number,
                    "repetitions": 8,
                    "weight": 60.0,
                    "rir": 2,
                }
                for number in (1, 2, 3)
            ],
        )
        connection.execute(
            classifications.insert(),
            [{"set_id": 20 + number, "is_warmup": False} for number in (1, 2, 3)],
        )
    assign_scheduled_session(engine, old_slot.day_id, logged, 2)
    configured = save_training_plan(
        engine,
        replace(original.draft, effective_from=date.today(), progression=settings),
        plan_id=original.plan_id,
    )
    next_slot = load_scheduled_workouts(engine, original.plan_id, next_day, next_day)[0]
    result = load_workout_recommendations(
        engine, original.plan_id, next_slot.day_id, next_day, as_of=date.today()
    )
    item = result.exercises[0]
    assert next_slot.version_id == configured.version_id
    assert item.reason_code == "one_more_rep"
    assert item.evidence_session_ids == (2,)
    assert [(goal.weight, goal.minimum) for goal in item.goals] == [(60.0, 9), (60.0, 8), (60.0, 8)]
    assert load_training_plan_version(engine, original.version_id).draft.progression is None


def test_readonly_service_uses_versioned_settings_and_cross_cycle_history(schedule_data):
    engine, _, source, sessions = schedule_data
    next_day = date.today() + timedelta(days=(0 - date.today().weekday()) % 7)
    origin, deload_day, last_normal = (
        next_day - timedelta(weeks=7),
        next_day - timedelta(weeks=1),
        next_day - timedelta(weeks=2),
    )
    settings = ProgressionSettings(origin, 7)
    plan = save_training_plan(
        engine,
        replace(
            source.draft,
            effective_from=origin,
            days=(replace(source.draft.days[0], name="Upper A", exercises=(PLAN,)),),
            progression=settings,
        ),
    )
    with engine.begin() as connection:
        for sid, day, reps, weight, rir, count in (
            (2, last_normal, 10, 60.0, 2, 3),
            (3, deload_day, 6, 52.5, 4, 2),
        ):
            connection.execute(
                sessions.update().where(sessions.c.session_id == sid).values(session_date=day)
            )
            connection.execute(
                actual_exercises.insert().values(
                    workout_exercise_id=sid * 100, session_id=sid, exercise_id=1
                )
            )
            connection.execute(
                actual_sets.insert(),
                [
                    {
                        "set_id": sid * 10 + number,
                        "workout_exercise_id": sid * 100,
                        "set_number": number,
                        "repetitions": reps,
                        "weight": weight,
                        "rir": rir,
                    }
                    for number in range(1, count + 1)
                ],
            )
            connection.execute(
                classifications.insert(),
                [
                    {"set_id": sid * 10 + number, "is_warmup": False}
                    for number in range(1, count + 1)
                ],
            )
    slots = load_scheduled_workouts(engine, plan.plan_id, last_normal, next_day)
    assign_scheduled_session(engine, slots[0].day_id, last_normal, 2)
    with engine.connect() as connection:
        before = connection.execute(select(actual_sets)).mappings().all()
    lighter = load_workout_recommendations(
        engine, plan.plan_id, slots[1].day_id, deload_day, as_of=deload_day
    )
    assert lighter.block.phase == "deload"
    assert lighter.exercises[0].goals[0].weight == 40.0
    assign_scheduled_session(engine, slots[1].day_id, deload_day, 3)
    # A normal revision must retain the anchor and support the preceding version's history.
    revised = save_training_plan(
        engine, replace(plan.draft, effective_from=next_day), plan_id=plan.plan_id
    )
    next_slot = load_scheduled_workouts(engine, plan.plan_id, next_day, next_day)[0]
    result = load_workout_recommendations(
        engine, plan.plan_id, next_slot.day_id, next_day, as_of=next_day
    )
    assert result.block.cycle == 2
    assert result.exercises[0].reason_code == "resume_after_deload"
    assert result.exercises[0].goals[0].weight == 60.0
    assert load_training_plan_version(engine, plan.version_id).draft.progression == settings
    rows = compute_plan_performance(
        load_plan_performance(engine, plan.plan_id, last_normal, next_day),
        as_of=next_day,
        settings_by_version={plan.version_id: settings, revised.version_id: settings},
    )
    assert next(row for row in rows if row["scheduled_date"] == deload_day)["missing_sets"] == 1
    from db.progression import load_normal_workout_recommendations

    with pytest.raises(ValueError, match="for deload dates"):
        load_normal_workout_recommendations(
            engine, plan.plan_id, slots[1].day_id, deload_day, as_of=deload_day
        )
    app = AppTest.from_string(
        """
import streamlit as st
from data_manager import DataManager
from ui.plan_adherence_view import PlanAdherenceView
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
PlanAdherenceView(manager=manager, exercise_names={1: "Bench Press"}, selected_month=st.session_state["test_month"]).render(mode="exercise")
""",
        default_timeout=30,
    )
    app.session_state["test_engine"] = engine
    app.session_state["test_month"] = deload_day.strftime("%Y-%m")
    app.session_state["adherence_plan"] = plan.plan_id
    app.run()
    assert not app.exception
    assert not app.error
    assert any("Deload: reduced training demand" in item.value for item in app.markdown)
    assert any("2/3 sets in range" in item.value for item in app.caption)
    with engine.connect() as connection:
        assert connection.execute(select(actual_sets)).mappings().all() == before
    with pytest.raises(ValueError, match="not scheduled"):
        load_workout_recommendations(engine, plan.plan_id, 999999, next_day, as_of=next_day)
