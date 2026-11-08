"""A plan revision retains usable observations without inheriting increases."""
from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from metrics.progression import recommend_workout
from metrics.recommendation_history import recommendation_history
from metrics.plan_performance import compute_plan_performance
from metrics.plan_adherence import compute_plan_adherence
from models.training_plan import ProgressionSettings, TrainingDay
from db.training_plans import save_training_plan, load_training_plan_versions
from db.plan_schedule import load_scheduled_workouts, assign_scheduled_session
from db.plan_adherence import load_plan_adherence, save_exercise_match, actual_exercises, actual_sets
from data_manager import DataManager
from ui.next_workout_view import approved_alternatives
from test_plan_schedule import schedule_data
from test_plan_performance import data
from test_progression import PLAN, AS_OF, BLOCK, recommend, upcoming, working


def other_workout(entry, name='Upper B'):
    workout, actual, match = entry
    return replace(workout, slot=replace(workout.slot, name=name)), actual, match


@pytest.mark.parametrize('change', [
    {'target_rir': 3}, {'target_min': 8}, {'target_max': 12},
])
def test_changed_prescription_retains_evidence_for_manual_start(change):
    old = working(1, date(2026, 5, 18), (10, 10, 10))
    planned = replace(PLAN, **change)
    result = recommend(old, target=upcoming(planned))
    assert (result.action, result.reason_code) == ('insufficient_data', 'manual_start')
    assert result.target_rir == planned.target_rir
    assert not result.goals
    assert result.evidence_session_ids == (1,)
    assert result.evidence_workouts == ('Upper A',)


def test_same_exercise_in_another_workout_supplies_a_baseline():
    source_plan = replace(PLAN, exercise_id=2, target_min=8, target_max=12, target_rir=1)
    entry = other_workout(working(1, date(2026, 5, 14), (7, 8, 7), planned=source_plan, actual_id=1, weight=90.3, rir=1))
    result = recommend(entry)
    assert result.reason_code == 'manual_start'
    assert result.actual_exercise_id == 1
    assert not result.goals
    assert result.evidence_dates == (date(2026, 5, 14),)
    assert result.evidence_workouts == ('Upper B',)


def test_another_exercise_is_never_a_baseline_without_explicit_selection():
    entry = other_workout(working(1, date(2026, 5, 14), actual_id=2))
    assert recommend(entry).reason_code == 'no_history'
    selected = recommend(entry, substitutions={101: 2})
    assert selected.reason_code == 'manual_start'
    assert selected.actual_exercise_id == 2


def test_reordered_exercise_keeps_a_baseline_without_carrying_confirmations():
    entry = working(1, date(2026, 5, 18), (10, 10, 10))
    # A different position in the earlier workout is enough to reset increases.
    rows = compute_plan_performance(data(entry), as_of=AS_OF)
    context = list(rows[0]['context'])
    context[3] = 4
    history, baseline = recommendation_history(rows, tuple(context), as_of=AS_OF, block_start=BLOCK)
    assert baseline and history[-1]['session_id'] == 1


@pytest.mark.parametrize('problem,expected', [
    ('partial', 'incomplete_sets'), ('empty', 'incomplete_sets'),
    ('missing_rir', 'missing_rir'), ('light', 'light_sets'),
])
def test_latest_local_problem_is_not_hidden_by_another_workout(problem, expected):
    entries = [working(1, date(2026, 5, 4))]
    last = working(2, date(2026, 5, 11), (8, 8) if problem == 'partial' else () if problem == 'empty' else (8, 8, 8),
                   rir=None if problem == 'missing_rir' else 4 if problem == 'light' else 2)
    if problem == 'light':
        last = (last[0], replace(last[1], sets=tuple(replace(s, is_warmup=None) for s in last[1].sets)), last[2])
    entries += [last, other_workout(working(3, date(2026, 5, 18), (10, 10, 10)))]
    result = recommend(*entries, target=upcoming(replace(PLAN, target_rir=3)))
    assert result.reason_code == expected
    assert not result.goals
    assert result.evidence_session_ids == (2,)


def test_a_new_context_needs_new_upper_range_confirmations():
    old = working(1, date(2026, 5, 4), (10, 10, 10))
    revised = replace(PLAN, target_rir=1)
    new = working(2, date(2026, 5, 18), (10, 10, 10), planned=revised)
    result = recommend(old, new, target=upcoming(revised))
    assert result.reason_code == 'upper_range_confirmed'
    assert all(goal.weight == 62.5 for goal in result.goals)


def test_baseline_preserves_mixed_loads_and_does_not_invent_new_sets():
    entry = working(1, date(2026, 5, 18))
    entry = (entry[0], replace(entry[1], sets=(replace(entry[1].sets[0], weight=80.), *entry[1].sets[1:])), entry[2])
    revised = replace(PLAN, target_rir=3)
    result = recommend(entry, target=upcoming(revised))
    assert result.reason_code == 'manual_start' and not result.goals
    result = recommend(entry, target=upcoming(replace(revised, set_count=4)))
    assert result.reason_code == 'changed_set_count' and not result.goals


def test_future_and_old_cross_workout_records_are_not_used_as_current_targets():
    old = other_workout(working(1, date(2026, 5, 4)))
    assert recommend(old, target=upcoming(day=date(2026, 6, 1))).reason_code == 'history_gap'
    future = other_workout(working(2, date(2026, 5, 21)))
    assert recommend(future).reason_code == 'no_history'


def test_block_reset_still_blocks_cross_workout_history():
    old = other_workout(working(1, date(2026, 5, 4)))
    result = recommend_workout(data(old), upcoming(), as_of=AS_OF,
        settings=ProgressionSettings(date(2026, 5, 15), 7))
    assert result.exercises[0].reason_code == 'no_normal_baseline'


def unplanned(sid=1, day=date(2026, 5, 18), values=(12, 12, 12), **options):
    workout, actual, _ = working(sid, day, values, planned=replace(PLAN, exercise_id=2), actual_id=1, **options)
    return workout, actual, None


def test_recorded_exercise_absent_from_old_plan_is_a_starting_load_without_inferred_replacement():
    entry = unplanned(weight=63.)
    result = recommend(entry)
    assert result.reason_code == 'manual_start'
    assert result.actual_exercise_id == 1
    assert not result.goals
    assert result.evidence_session_ids == (1,)
    assert compute_plan_adherence(data(entry), as_of=AS_OF)['summary']['covered_sets'] == 0
    assert data(entry).matches == ()
    assert not any(row['actual_exercise_id'] == 1 for row in compute_plan_performance(data(entry), as_of=AS_OF))


def test_todays_extra_exercise_linked_to_yesterdays_slot_uses_actual_date():
    entry = unplanned(day=date(2026, 5, 19), weight=63.)
    entry = (replace(entry[0], slot=replace(entry[0].slot, performed_on=AS_OF)), entry[1], None)
    result = recommend(entry)
    assert result.reason_code == 'manual_start'
    assert result.evidence_dates == (AS_OF,)
    assert result.evidence_workouts == ('Upper A',)


@pytest.mark.parametrize('problem,expected', [
    ('partial', 'incomplete_sets'), ('missing_rir', 'missing_rir'), ('warmup', 'incomplete_sets'),
    ('light', 'light_sets'), ('future', 'no_history'),
])
def test_unplanned_baselines_respect_latest_evidence_barriers(problem, expected):
    older = unplanned(1, date(2026, 5, 11))
    latest = unplanned(2, date(2026, 5, 18), (12, 12) if problem == 'partial' else (12, 12, 12),
                       rir=None if problem == 'missing_rir' else 4 if problem == 'light' else 2)
    if problem in ('warmup', 'light'):
        latest = (latest[0], replace(latest[1], sets=tuple(replace(s, is_warmup=True if problem == 'warmup' else None)
                                                         for s in latest[1].sets)), None)
    if problem == 'future':
        latest = (replace(latest[0], slot=replace(latest[0].slot, performed_on=date(2026, 5, 21))), latest[1], None)
        entries = (latest,)
    else:
        entries = (older, latest)
    result = recommend(*entries)
    assert result.reason_code == expected and not result.goals


def test_unplanned_upper_range_results_do_not_count_as_weight_increase_confirmations():
    first = unplanned(1, date(2026, 5, 11), (10, 10, 10))
    second = unplanned(2, date(2026, 5, 18), (10, 10, 10))
    result = recommend(first, second)
    assert result.reason_code == 'manual_start'
    assert not result.goals
    first_planned = working(2, date(2026, 5, 18), (10, 10, 10))
    assert recommend(first, first_planned).reason_code == 'upper_range_confirmed'


def test_unlinked_exercise_and_another_catalog_id_do_not_supply_starting_loads():
    entry = unplanned()
    detached = (replace(entry[0], slot=replace(entry[0].slot, session_id=None, performed_on=None)), entry[1], None)
    assert recommend(detached).reason_code == 'no_history'
    different = (entry[0], replace(entry[1], exercise_id=3), None)
    assert recommend(different).reason_code == 'no_history'


@pytest.fixture
def revised_plan_history(schedule_data):
    from datetime import timedelta
    engine, _, source, sessions = schedule_data
    today = date.today()
    monday = today - timedelta(days=today.weekday() + 7)
    thursday = monday + timedelta(days=3)
    next_monday = today + timedelta(days=7 - today.weekday())
    names = {1: 'Barbell Bench Press', 2: 'Incline Machine Chest Press', 3: 'Seated Cable Row',
             4: 'Pronated-Grip Pull-Up', 5: 'Lat Pulldown', 6: 'Machine Chest Press'}
    with engine.begin() as connection:
        connection.execute(text('INSERT INTO exercises (exercise_id, exercise_name) VALUES (:id, :name)'),
            [{'id': key, 'name': value} for key, value in names.items() if key != 1])
    plans = [replace(PLAN, exercise_id=key, target_rir=1) for key in (1, 2, 4, 3)]
    first = save_training_plan(engine, replace(source.draft, effective_from=monday,
        days=(TrainingDay('Upper A', 0, tuple(plans)), TrainingDay('Upper B', 3, (replace(PLAN, exercise_id=5, target_rir=1),))),
        progression=ProgressionSettings(monday, 7)))
    slots = load_scheduled_workouts(engine, first.plan_id, monday, thursday)
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=monday))
        connection.execute(sessions.update().where(sessions.c.session_id == 3).values(session_date=thursday))
        for we_id, sid, ex_id, weights, reps, reserves in (
            (201, 2, 6, (85.,) * 3, (9, 9, 11), (2, 2, 0)),
            (202, 2, 2, (80., 70., 70.), (7, 11, 11), (1, 1, 0)),
            (203, 2, 5, (70.,) * 3, (12, 12, 11), (2, 1, 1)),
            (204, 2, 3, (85.,) * 3, (9, 9, 9), (2, 2, 1)),
            (301, 3, 4, (90.3,) * 3, (7, 8, 7), (1, 1, 1)),
        ):
            connection.execute(actual_exercises.insert().values(workout_exercise_id=we_id, session_id=sid, exercise_id=ex_id))
            connection.execute(actual_sets.insert(), [dict(workout_exercise_id=we_id, set_number=index,
                repetitions=rep, weight=weight, rir=rir) for index, (weight, rep, rir) in enumerate(zip(weights, reps, reserves), 1)])
    for slot, sid in zip(slots, (2, 3)):
        assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, sid)
        targets = load_plan_adherence(engine, first.plan_id, slot.scheduled_date, slot.scheduled_date).workouts[0].targets
        if sid == 2:
            save_exercise_match(engine, 2, targets[0].plan_exercise_id, 201)
            save_exercise_match(engine, 2, targets[2].plan_exercise_id, 203)
        else:
            save_exercise_match(engine, 3, targets[0].plan_exercise_id, 301)
    revised = save_training_plan(engine, replace(first.draft, effective_from=today,
        days=(replace(first.draft.days[0], exercises=tuple(replace(p, target_rir=2) for p in plans)), first.draft.days[1])), plan_id=first.plan_id)
    dm = object.__new__(DataManager)
    dm.engine = engine
    return dm, revised, next_monday, monday, thursday, names


def test_database_revision_recovers_local_and_cross_workout_baselines(revised_plan_history):
    dm, plan, next_day, monday, thursday, names = revised_plan_history
    slot = next(s for s in dm.load_scheduled_workouts(plan.plan_id, next_day, next_day) if s.name == 'Upper A')
    result = dm.load_workout_recommendations(plan.plan_id, slot.day_id, next_day, as_of=date.today())
    bench, incline, pullup, row = result.exercises
    assert bench.actual_exercise_id == 1 and not bench.goals
    for item in (incline, pullup, row):
        assert item.reason_code == 'manual_start'
        assert item.target_rir == 2
    assert not incline.goals
    assert row.evidence_dates == (monday,)
    assert pullup.evidence_dates == (thursday,)
    assert pullup.evidence_workouts == ('Upper B',)
    history = dm.load_plan_performance(plan.plan_id, next_day, next_day)
    planned = dm.load_scheduled_workout_targets(slot.day_id)
    alternatives = approved_alternatives(history, slot, planned.exercises, as_of=date.today())
    assert alternatives[1] == [6]
    chosen = dm.load_workout_recommendations(plan.plan_id, slot.day_id, next_day, as_of=date.today(),
        substitutions={bench.plan_exercise_id: 6})
    assert chosen.exercises[0].actual_exercise_id == 6
    assert chosen.exercises[0].reason_code == 'manual_start'
    assert chosen.exercises[0].evidence_dates == (monday,)


def test_preview_displays_source_dates_and_confirmed_alternative_after_revision(revised_plan_history):
    dm, plan, next_day, monday, thursday, names = revised_plan_history
    app = AppTest.from_string('''
import streamlit as st
from ui.next_workout_view import NextWorkoutView
NextWorkoutView(st.session_state['manager'], st.session_state['names']).render(
    st.session_state['plan_id'], st.session_state['versions'])
''', default_timeout=30)
    app.session_state['manager'] = dm
    app.session_state['names'] = names
    app.session_state['plan_id'] = plan.plan_id
    app.session_state['versions'] = load_training_plan_versions(dm.engine, plan.plan_id)
    app.run()
    assert not app.exception
    slot = next(s for s in dm.load_scheduled_workouts(plan.plan_id, next_day, next_day) if s.name == 'Upper A')
    app.selectbox(key=f'next_workout_{plan.plan_id}').select(f'{slot.day_id}:{next_day}').run()
    assert not app.exception
    html = '\n'.join(item.value for item in app.markdown)
    assert 'Seated Cable Row' in html and 'Choose starting load' in html
    assert f'{thursday:%d %b %Y} · Upper B' in html
    assert f'{monday:%d %b %Y} · Upper A' in html
    alternative = next(item for item in app.selectbox if item.key.endswith('_exercise'))
    alternative.select(6).run()
    assert not app.exception
    html = '\n'.join(item.value for item in app.markdown)
    assert 'Instead of Barbell Bench Press' in html
    assert 'Choose starting load' in html
