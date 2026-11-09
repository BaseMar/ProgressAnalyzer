"""Historical references and manual choices must not manufacture progression evidence."""
from dataclasses import replace
from datetime import date

from sqlalchemy import select

from db.plan_adherence import actual_exercises, actual_sets
from db.plan_schedule import links, load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.recommendation_references import load_recommendation_references
from db.training_plans import save_training_plan
from metrics.overview_summary import workout_focus
from models.progression import WorkoutRecommendation
from test_next_workout_view import AS_OF, NEXT, exercise_html, start_app
from test_plan_schedule import schedule_data
from test_recommendation_history import revised_plan_history


def snapshot(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(select(table)).all() for table in (actual_sets, links))


def test_unlinked_history_before_plan_supplies_starting_loads_without_progression(schedule_data):
    engine, _, source, sessions = schedule_data
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=date(2026,4,27)))
        connection.execute(sessions.update().where(sessions.c.session_id == 3).values(session_date=date(2026,5,26)))
        for sid in (2,3):
            for occurrence in (0,1):
                we_id=sid*100+occurrence
                connection.execute(actual_exercises.insert().values(workout_exercise_id=we_id,session_id=sid,exercise_id=1))
                connection.execute(actual_sets.insert().values(workout_exercise_id=we_id,set_number=1,weight=90.,repetitions=8,rir=1))
    before=snapshot(engine)
    references=load_recommendation_references(engine,{1},as_of=AS_OF)
    assert len(references[1])==2
    assert {r['session_id'] for r in references[1]}=={2}
    assert all(r['date']==date(2026,4,27) and r['workout'] is None for r in references[1])
    # Old unlinked entries supply loads without confirming a weight increase.
    plan=seed_without_records(engine,source)
    app=start_app(engine,plan)
    html=exercise_html(app)
    assert '27 Apr 2026' in html and '90 kg' in html
    assert 'Starting loads' in html
    assert '3 × 6–10 reps · RIR ≥ 2' in html
    assert 'Target not available yet' not in html
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert snapshot(engine)==before
    slot=load_scheduled_workouts(engine,plan.plan_id,NEXT,NEXT)[0]
    result=load_workout_recommendations(engine,plan.plan_id,slot.day_id,NEXT,as_of=AS_OF)
    assert result.exercises[0].reason_code == 'reuse_exercise_baseline'
    assert [g.weight for g in result.exercises[0].goals] == [90.] * 3


def seed_without_records(engine,source):
    from models.training_plan import ProgressionSettings,TrainingDay
    from test_progression import PLAN
    return save_training_plan(engine,replace(source.draft,effective_from=date(2026,5,4),
        days=(TrainingDay('Upper A',0,(PLAN,)),),progression=ProgressionSettings(date(2026,5,4),7)))


def test_manual_fallback_without_history_saves_across_dates_and_browser_sessions(schedule_data):
    engine,_,source,_=schedule_data
    revised=seed_without_records(engine,source)
    before=snapshot(engine)
    app=start_app(engine,revised)
    inputs=[n for n in app.number_input if n.key.startswith('manual_start_')]
    assert len(inputs)==3 and all(n.value is None for n in inputs)
    for field in inputs:
        field.set_value(55.)
    app.run()
    assert not app.exception
    assert 'Starting loads selected' in exercise_html(app)
    assert '55 kg · 3 × 6–10 reps · RIR ≥ 2' in exercise_html(app)
    assert any('__x55 / __x55 / __x55' in c.value for c in app.code)
    assert 'Choose starting loads' not in [expander.label for expander in app.expander]
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert snapshot(engine)==before
    slot=load_scheduled_workouts(engine,revised.plan_id,NEXT,NEXT)[0]
    original=load_workout_recommendations(engine,revised.plan_id,slot.day_id,NEXT,as_of=AS_OF)
    assert original.exercises[0].reason_code=='no_normal_baseline' and not original.exercises[0].goals
    other=load_scheduled_workouts(engine,revised.plan_id,date(2026,6,1),date(2026,6,1))[0]
    app.selectbox(key=f'next_workout_{revised.plan_id}').select(f'{other.day_id}:{other.scheduled_date}').run()
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert '55 kg' in exercise_html(app)
    fresh = start_app(engine, revised)
    assert not [n for n in fresh.number_input if n.key.startswith('manual_start_')]
    assert 'Saved starting loads' in exercise_html(fresh)
    fresh.toggle[0].set_value(True).run()
    assert [n.value for n in fresh.number_input if n.key.startswith('manual_start_')] == [55., 55., 55.]
    next(n for n in fresh.number_input if n.key.startswith('manual_start_')).set_value(50.).run()
    app.toggle[0].set_value(True).run()
    assert [n.value for n in app.number_input if n.key.startswith('manual_start_')] == [50., 55., 55.]
    app.toggle[0].set_value(False).run()
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert not [e for e in app.expander if e.label in ('Choose starting loads', 'Edit starting loads')]
    app.toggle[0].set_value(True).run()
    assert [n.value for n in app.number_input if n.key.startswith('manual_start_')] == [50., 55., 55.]


def test_manual_start_readiness_does_not_count_an_unselected_start():
    from models.progression import ExerciseRecommendation,SetGoal,TrainingBlockPhase
    item=ExerciseRecommendation(1,1,1,NEXT,'insufficient_data',(),2,'manual_start','')
    phase=TrainingBlockPhase('normal')
    assert workout_focus(WorkoutRecommendation(phase,(item,))).available==0
    selected=replace(item,goals=(SetGoal(55.,6,10,'reps'),)*3,reason_code='manual_start_selected')
    focus=workout_focus(WorkoutRecommendation(phase,(selected,)))
    assert focus.available==1 and not focus.gaps


def test_bodyweight_manual_choice_does_not_reinterpret_legacy_kilograms(revised_plan_history):
    from streamlit.testing.v1 import AppTest
    from db.training_plans import load_training_plan_versions
    dm,plan,next_day,_,_,names=revised_plan_history
    app=AppTest.from_string('''
import streamlit as st
from ui.next_workout_view import NextWorkoutView
NextWorkoutView(st.session_state['manager'],st.session_state['names']).render(
    st.session_state['plan_id'],st.session_state['versions'])
''',default_timeout=30)
    app.session_state['manager']=dm
    app.session_state['names']=names
    app.session_state['plan_id']=plan.plan_id
    app.session_state['versions']=load_training_plan_versions(dm.engine,plan.plan_id)
    app.run()
    slot=next(s for s in dm.load_scheduled_workouts(plan.plan_id,next_day,next_day) if s.name=='Upper A')
    app.selectbox(key=f'next_workout_{plan.plan_id}').select(f'{slot.day_id}:{next_day}').run()
    fields=[n for n in app.number_input if 'Pull-Up' in n.label]
    assert len(fields)==3
    assert all('additional load (kg)' in n.label and n.value is None for n in fields)
    assert '90.3 kg recorded' in exercise_html(app)
    for field in fields:
        field.set_value(0.)
    app.run()
    assert not app.exception
    assert 'bodyweight + 0 kg' in exercise_html(app)
    assert '90.3 kg ×' not in exercise_html(app)


def test_saved_start_is_replaced_by_actual_training_history(schedule_data):
    from db.plan_schedule import assign_scheduled_session
    engine, _, source, sessions = schedule_data
    plan = seed_without_records(engine, source)
    app = start_app(engine, plan)
    for field in app.number_input:
        if field.key.startswith('manual_start_'):
            field.set_value(55.)
    app.run()
    assert 'Saved starting loads' in exercise_html(app)
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=date(2026, 5, 18)))
        connection.execute(actual_exercises.insert().values(workout_exercise_id=200, session_id=2, exercise_id=1))
        connection.execute(actual_sets.insert(), [dict(workout_exercise_id=200, set_number=n,
            weight=60., repetitions=10, rir=2) for n in (1, 2, 3)])
    slot = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))[0]
    assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, 2)
    app.run()
    assert not app.exception
    assert 'Increase load' in exercise_html(app)
    assert '62.5 kg' in exercise_html(app)
    assert 'Saved starting loads' not in exercise_html(app)
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]


def test_setup_stays_until_every_exercise_is_saved_then_hides(schedule_data):
    from models.training_plan import ProgressionSettings, TrainingDay
    from test_progression import PLAN
    engine, _, source, _ = schedule_data
    plan = save_training_plan(engine, replace(source.draft, effective_from=date(2026, 5, 4),
        days=(TrainingDay('Upper A', 0, (PLAN, PLAN)),),
        progression=ProgressionSettings(date(2026, 5, 4), 7)))
    app = start_app(engine, plan)
    inputs = [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert len(inputs) == 6
    for field in inputs[:3]:
        field.set_value(55.)
    app.run()
    assert 'Choose starting loads' in [e.label for e in app.expander]
    assert [n.value for n in app.number_input if n.key.startswith('manual_start_')] == [55., 55., 55., None, None, None]
    for field in list(app.number_input)[3:]:
        field.set_value(50.)
    app.run()
    assert not app.exception
    assert 'Choose starting loads' not in [e.label for e in app.expander]
    assert not [n for n in app.number_input if n.key.startswith('manual_start_')]
    assert exercise_html(app).count('Saved starting loads') == 2
    app.run()
    assert not app.exception
    assert 'Choose starting loads' not in [e.label for e in app.expander]
    assert '55 kg' in exercise_html(app) and '50 kg' in exercise_html(app)
    app.toggle[0].set_value(True).run()
    assert [n.value for n in app.number_input if n.key.startswith('manual_start_')] == [55., 55., 55., 50., 50., 50.]


def test_missing_storage_keeps_preview_available_and_explains_unsaved_choices(schedule_data):
    from db.starting_loads import starting_loads
    engine, _, source, _ = schedule_data
    with engine.begin() as connection:
        starting_loads.drop(connection)
    plan = seed_without_records(engine, source)
    app = start_app(engine, plan)
    assert any('saving is unavailable' in warning.value for warning in app.warning)
    for field in app.number_input:
        if field.key.startswith('manual_start_'):
            field.set_value(55.)
    app.run()
    assert not app.exception
    assert 'Starting loads selected' in exercise_html(app)
    assert 'Saved starting loads' not in exercise_html(app)
