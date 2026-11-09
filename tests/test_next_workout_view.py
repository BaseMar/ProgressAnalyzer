"""Real Streamlit reruns for next-session selection, alternatives and target states."""
from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from streamlit.testing.v1 import AppTest

from test_plan_schedule import schedule_data
from test_progression import PLAN
from db.plan_adherence import actual_exercises, actual_sets, load_plan_adherence, save_exercise_match
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.set_classifications import classifications
from db.training_plans import save_training_plan
from models.progression import ExerciseRecommendation, SetGoal
from models.training_plan import ProgressionSettings, TrainingDay
from ui.next_workout_view import goal_summary

START = date(2026, 5, 4)
AS_OF = date(2026, 5, 20)
NEXT = date(2026, 5, 25)

APP = '''
import streamlit as st
from data_manager import DataManager
from ui.next_workout_view import NextWorkoutView
from db.training_plans import load_training_plan_versions
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
versions = load_training_plan_versions(manager.engine, st.session_state["plan_id"])
NextWorkoutView(manager, {1: "Barbell Bench Press", 2: "Machine Chest Press"}).render(
    st.session_state["plan_id"], versions, as_of=st.session_state["as_of"])
'''


def seed(schedule_data, *, planned=PLAN, actual_id=1, classification=False, rir=2, progression=True):
    engine, _, source, sessions = schedule_data
    plan = save_training_plan(engine, replace(source.draft, name="Strength block", effective_from=START,
        days=(TrainingDay("Upper A", 0, (planned,)),),
        progression=ProgressionSettings(START, 7) if progression else None))
    if actual_id == 2:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO exercises (exercise_id, exercise_name) VALUES (2, 'Machine Chest Press')"))
    with engine.begin() as connection:
        for sid, day in ((2, date(2026, 5, 11)), (3, date(2026, 5, 18))):
            connection.execute(sessions.update().where(sessions.c.session_id == sid).values(session_date=day))
            connection.execute(actual_exercises.insert().values(workout_exercise_id=sid * 100, session_id=sid, exercise_id=actual_id))
            connection.execute(actual_sets.insert(), [{"set_id": sid * 10 + number, "workout_exercise_id": sid * 100,
                "set_number": number, "repetitions": 10, "weight": 60., "rir": rir} for number in (1, 2, 3)])
            if classification is not None:
                connection.execute(classifications.insert(), [{"set_id": sid * 10 + number, "is_warmup": classification} for number in (1, 2, 3)])
    slots = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 11), NEXT)
    for sid, slot in zip((2, 3), slots):
        assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, sid)
        if actual_id != 1:
            target = load_plan_adherence(engine, plan.plan_id, slot.scheduled_date, slot.scheduled_date).workouts[0].targets[0]
            save_exercise_match(engine, sid, target.plan_exercise_id, sid * 100)
    return plan


def start_app(engine, plan, as_of=AS_OF):
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["plan_id"] = plan.plan_id
    app.session_state["as_of"] = as_of
    app.run()
    assert not app.exception
    assert not app.error
    return app


def rendered(app):
    return "\n".join(item.value for item in app.markdown)


def exercise_html(app):
    return next(item.value for item in app.markdown if 'class="recommendation-list"' in item.value)


def test_next_normal_goal_and_evidence_render_without_changing_logged_data(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data)
    with engine.connect() as connection:
        before = connection.execute(select(actual_sets)).mappings().all()
    app = start_app(engine, plan)
    assert app.selectbox(key=f"next_workout_{plan.plan_id}").value.endswith(str(NEXT))
    assert "62.5 kg · 3 × 6 reps · RIR ≥ 2" in exercise_html(app)
    assert "Increase load" in exercise_html(app)
    assert any("session #3" in item.value for item in app.caption)
    assert not app.dataframe
    with engine.connect() as connection:
        assert connection.execute(select(actual_sets)).mappings().all() == before


def test_deload_and_return_render_as_different_decisions(schedule_data):
    engine, _, _, sessions = schedule_data
    plan = seed(schedule_data)
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 3).values(session_date=date(2026, 6, 8)))
    # Move the latest log to the last normal Monday rather than leaving an old slot linked.
    from db.plan_schedule import unassign_scheduled_session
    old = load_scheduled_workouts(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))[0]
    unassign_scheduled_session(engine, old.day_id, old.scheduled_date, 3)
    normal = load_scheduled_workouts(engine, plan.plan_id, date(2026, 6, 8), date(2026, 6, 8))[0]
    assign_scheduled_session(engine, normal.day_id, normal.scheduled_date, 3)
    app = start_app(engine, plan, as_of=date(2026, 6, 15))
    assert "40 kg · 3 × 10 reps · RIR 3–4" in exercise_html(app)
    assert "recommendation-phase--deload" in rendered(app)
    key = f"{normal.day_id}:2026-06-22"
    app.selectbox(key=f"next_workout_{plan.plan_id}").select(key).run()
    assert not app.exception
    assert "Return after deload" in exercise_html(app)
    assert "60 kg · 3 × 6–10 reps · RIR ≥ 2" in exercise_html(app)


@pytest.mark.parametrize("options, text_expected", [
    ({"planned": replace(PLAN, target_rir=None)}, "Set target RIR"),
    ({"planned": replace(PLAN, weight_increment=None)}, "Set the available weight step"),
])
def test_missing_data_gives_a_specific_next_action_and_no_invented_numeric_goal(schedule_data, options, text_expected):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, **options)
    app = start_app(engine, plan)
    html = exercise_html(app)
    assert "More data needed" in html
    assert "Target not available yet" in html
    assert text_expected in html
    assert "62.5 kg" not in html


def test_missing_source_rir_keeps_recorded_starting_loads_without_increasing_them(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, rir=None)
    app = start_app(engine, plan)
    html = exercise_html(app)
    assert 'Starting loads' in html and '60 kg' in html
    assert 'Source RIR is incomplete' in html
    assert '62.5 kg' not in html
    assert 'Choose starting loads' not in [e.label for e in app.expander]


def test_legacy_plan_has_ordinary_targets_without_a_calendar(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, progression=False)
    app = start_app(engine, plan)
    assert any("Ordinary progression is available" in item.value for item in app.caption)
    assert "62.5 kg" in exercise_html(app)


def test_automatic_working_sets_need_no_label_editor_before_recommendations(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, classification=None)
    app = start_app(engine, plan)
    assert "Increase load" in exercise_html(app)
    assert "62.5 kg · 3 × 6 reps" in exercise_html(app)
    with engine.connect() as connection:
        assert connection.execute(select(classifications)).all() == []


def test_not_started_block_explains_date_and_offers_later_workouts(schedule_data):
    engine, _, source, _ = schedule_data
    plan = save_training_plan(engine, replace(source.draft, effective_from=START,
        progression=ProgressionSettings(date(2026, 6, 1), 7)))
    app = start_app(engine, plan)
    assert any("starts on 01 Jun 2026" in item.value for item in app.info)
    next_slot = load_scheduled_workouts(engine, plan.plan_id, date(2026, 6, 1), date(2026, 6, 1))[0]
    app.selectbox(key=f"next_workout_{plan.plan_id}").select(f"{next_slot.day_id}:2026-06-01").run()
    assert not app.exception
    assert "establish a baseline" in exercise_html(app)


def test_confirmed_alternative_uses_own_history_step_and_resets_for_another_date(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, actual_id=2)
    app = start_app(engine, plan)
    assert "Choose starting load" in exercise_html(app)
    selector = next(item for item in app.selectbox if item.key.endswith("_exercise"))
    selector.select(2).run()
    assert not app.exception
    assert "Machine Chest Press" in exercise_html(app)
    assert "Instead of Barbell Bench Press" in exercise_html(app)
    assert "Enter a positive weight step" in exercise_html(app)
    step = next(item for item in app.number_input if "Weight step" in item.label)
    step.set_value(5.).run()
    assert not app.exception
    assert "65 kg · 3 × 6 reps" in exercise_html(app)
    next_slot = load_scheduled_workouts(engine, plan.plan_id, NEXT + timedelta(days=7), NEXT + timedelta(days=7))[0]
    app.selectbox(key=f"next_workout_{plan.plan_id}").select(f"{next_slot.day_id}:{next_slot.scheduled_date}").run()
    assert not app.exception
    assert "Instead of" not in exercise_html(app)
    assert next(item for item in app.selectbox if item.key.endswith("_exercise")).value == 1
    original = load_plan_adherence(engine, plan.plan_id, date(2026, 5, 18), date(2026, 5, 18))
    assert original.matches[0].workout_exercise_id == 300
    assert not any(slot.session_id for slot in load_scheduled_workouts(engine, plan.plan_id, NEXT, NEXT + timedelta(days=7)))


def test_new_session_link_invalidates_old_selection_instead_of_showing_stale_targets(schedule_data):
    engine, _, _, sessions = schedule_data
    plan = seed(schedule_data)
    app = start_app(engine, plan)
    slot = load_scheduled_workouts(engine, plan.plan_id, NEXT, NEXT)[0]
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 1).values(session_date=NEXT))
    assign_scheduled_session(engine, slot.day_id, NEXT, 1)
    app.run()
    assert not app.exception
    assert app.selectbox(key=f"next_workout_{plan.plan_id}").value.endswith("2026-06-01")


def test_future_plan_and_same_date_workouts_have_stable_distinct_choices(schedule_data):
    engine, _, source, _ = schedule_data
    first = date(2027, 1, 4)
    day = TrainingDay("Upper A", 0, (PLAN,))
    plan = save_training_plan(engine, replace(source.draft, effective_from=first,
        days=(day, replace(day, name="Upper B")), progression=ProgressionSettings(first, 7)))
    app = start_app(engine, plan)
    choices = app.selectbox(key=f"next_workout_{plan.plan_id}")
    assert choices.value.endswith("2027-01-04")
    assert len([option for option in choices.options if "04 Jan 2027" in option]) == 2


def test_goal_summary_preserves_unequal_sets_and_zero_rir():
    item = ExerciseRecommendation(1, 1, 1, NEXT, "increase_reps", (
        SetGoal(60., 10, 10, "reps"), SetGoal(60., 9, 9, "reps"), SetGoal(60., 8, 8, "reps")), 0, "one_more_rep", "")
    assert goal_summary(item) == "60 kg · 10 / 9 / 8 reps · RIR ≥ 0"
    mixed = replace(item, goals=(SetGoal(60., 6, 10, "reps"), SetGoal(65., 6, 10, "reps")))
    assert "S1: 60 kg × 6–10 reps" in goal_summary(mixed)
    assert "S2: 65 kg × 6–10 reps" in goal_summary(mixed)


def test_historical_analytics_has_no_duplicate_next_workout(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data)
    app = AppTest.from_string('''
import streamlit as st
from data_manager import DataManager
from ui.plan_adherence_view import PlanAdherenceView
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
PlanAdherenceView(manager=manager, exercise_names={1: "Bench Press"}, selected_month="2026-05").render()
''', default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["adherence_plan"] = plan.plan_id
    app.run()
    assert not app.exception
    assert not any(item.label == "Upcoming workout" for item in app.selectbox)
    assert not any('class="recommendation-list"' in item.value for item in app.markdown)
    assert [item.value for item in app.metric] == ['2/4', '50%', '100%']
    assert 'An unlinked workout is not proof it was skipped' in app.metric[0].proto.help


def test_card_failure_does_not_raise_or_hide_rest_of_page():
    app = AppTest.from_string('''
import streamlit as st
from types import SimpleNamespace
from datetime import date
from sqlalchemy.exc import OperationalError
from ui.next_workout_view import NextWorkoutView
def fail(*args):
    raise OperationalError("schedule read", {}, Exception("unavailable"))
manager = SimpleNamespace(load_scheduled_workouts=fail)
version = SimpleNamespace(draft=SimpleNamespace(effective_from=date.today()))
NextWorkoutView(manager).render(1, [version])
st.caption("Historical analysis remains visible")
''')
    app.run()
    assert not app.exception
    assert any("could not be loaded" in item.value for item in app.error)
    assert any("Historical analysis remains visible" in item.value for item in app.caption)
