"""Execution coverage, confirmed substitutes, and their persistence lifecycle."""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from test_plan_schedule import schedule_data
from db.plan_adherence import (
    actual_exercises, actual_sets, load_plan_adherence, matches,
    remove_exercise_match, save_exercise_match,
)
from db.plan_schedule import assign_scheduled_session, unassign_scheduled_session
from db.training_plans import save_training_plan
from metrics.plan_adherence import compute_plan_adherence
from models.plan_adherence import ExerciseMatch, PlanAdherenceInput, PlannedTarget, PlannedWorkout, RecordedExercise
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise, TrainingDay
from models.workout_set import WorkoutSet

TODAY = date(2026, 5, 20)


def example(*, actual_id=1, count=3, approved=False):
    slot = ScheduledWorkout(10, 1, date(2026, 5, 18), "Upper", 1, date(2026, 5, 19))
    target = PlannedTarget(101, PlannedExercise(1, 3, 6, 10))
    actual = RecordedExercise(201, 1, actual_id, tuple(WorkoutSet(201, index, 8, 50., None) for index in range(count)))
    return PlanAdherenceInput((PlannedWorkout(slot, (target,)),), (actual,),
                              (ExerciseMatch(1, 101, 201),) if approved else ())


def test_substitute_counts_only_after_confirmation_and_preserves_actual_identity():
    data = example(actual_id=2)
    before = compute_plan_adherence(data, as_of=TODAY)
    assert before["summary"]["covered_sets"] == 0
    approved = replace(data, matches=(ExerciseMatch(1, 101, 201),))
    after = compute_plan_adherence(approved, as_of=TODAY)
    assert after["summary"]["complete_workouts"] == 1
    assert after["summary"]["covered_sets"] == 3
    assert after["summary"]["on_time_workouts"] == 0
    assert after["workouts"][0]["details"][0]["replacement_exercise_id"] == 2
    assert approved.recorded[0].exercise_id == 2
    assert approved.workouts[0].targets[0].exercise.exercise_id == 1


def test_extra_sets_are_capped_and_missing_exercises_leave_workout_partial():
    data = example(count=8)
    workout = data.workouts[0]
    data = replace(data, workouts=(replace(workout, targets=(*workout.targets,
        PlannedTarget(102, PlannedExercise(3, 2, 8, 12)),
    )),))
    report = compute_plan_adherence(data, as_of=TODAY)
    assert report["summary"]["covered_sets"] == 3
    assert report["summary"]["planned_sets"] == 5
    assert report["summary"]["covered_exercises"] == 1
    assert report["workouts"][0]["status"] == "Partial"


def test_repeated_planned_exercise_cannot_count_recorded_sets_twice():
    data = example(count=4)
    data = replace(data, workouts=(replace(data.workouts[0], targets=(
        *data.workouts[0].targets, PlannedTarget(102, PlannedExercise(1, 3, 6, 10)),
    )),))
    report = compute_plan_adherence(data, as_of=TODAY)
    assert [item["covered_sets"] for item in report["workouts"][0]["details"]] == [3, 1]
    assert report["summary"]["covered_sets"] == 4


def test_explicit_replacement_reserves_exercise_before_exact_matching():
    data = example(actual_id=2, approved=True)
    data = replace(data, workouts=(replace(data.workouts[0], targets=(
        PlannedTarget(102, PlannedExercise(2, 3, 6, 10)), *data.workouts[0].targets,
    )),))
    report = compute_plan_adherence(data, as_of=TODAY)
    assert [item["covered_sets"] for item in report["workouts"][0]["details"]] == [0, 3]
    assert report["summary"]["covered_sets"] == 3


def test_today_and_future_do_not_change_summary_denominators_or_numerators():
    data = example()
    old = replace(data.workouts[0], slot=replace(data.workouts[0].slot, session_id=None, performed_on=None))
    today = replace(old, slot=replace(old.slot, scheduled_date=TODAY))
    early = replace(data.workouts[0], slot=replace(data.workouts[0].slot, scheduled_date=TODAY + timedelta(days=7)))
    report = compute_plan_adherence(replace(data, workouts=(old, today, early)), as_of=TODAY)
    assert report["summary"]["due_workouts"] == 1
    assert report["summary"]["linked_workouts"] == 0
    assert report["summary"]["covered_sets"] == 0
    assert report["workouts"][0]["status"] == "Not recorded"
    assert report["workouts"][1]["status"] == "Due today"
    assert not report["workouts"][2]["eligible"]


def test_timed_sets_do_not_automatically_satisfy_repetition_targets():
    data = example()
    actual = replace(data.recorded[0], sets=(WorkoutSet(201, 1, 0, 0., None, 60),))
    report = compute_plan_adherence(replace(data, recorded=(actual,)), as_of=TODAY)
    assert report["summary"]["covered_sets"] == 0


def test_future_recorded_session_does_not_earn_credit_as_of_today():
    data = example()
    data = replace(data, workouts=(replace(data.workouts[0], slot=replace(
        data.workouts[0].slot, performed_on=TODAY + timedelta(days=1),
    )),))
    assert compute_plan_adherence(data, as_of=TODAY)["summary"]["covered_sets"] == 0


def seed_alternative(engine):
    with engine.begin() as connection:
        connection.execute(actual_exercises.insert(), [
            {"workout_exercise_id": 200, "session_id": 2, "exercise_id": 2},
            {"workout_exercise_id": 300, "session_id": 3, "exercise_id": 2},
        ])
        connection.execute(actual_sets.insert(), [{
            "workout_exercise_id": we_id, "set_number": number, "repetitions": 8,
            "weight": 50., "rir": None, "duration_seconds": None,
        } for we_id in (200, 300) for number in (1, 2, 3)])


def linked_report(schedule_data):
    engine, start, plan, _ = schedule_data
    seed_alternative(engine)
    data = load_plan_adherence(engine, plan.plan_id, start, start)
    assign_scheduled_session(engine, data.workouts[0].slot.day_id, start, 2)
    return load_plan_adherence(engine, plan.plan_id, start, start)


def test_confirm_and_remove_replacement_roundtrip_without_modifying_training_logs(schedule_data):
    engine, start, plan, _ = schedule_data
    data = linked_report(schedule_data)
    target_id = data.workouts[0].targets[0].plan_exercise_id
    save_exercise_match(engine, 2, target_id, 200)
    report = compute_plan_adherence(load_plan_adherence(engine, plan.plan_id, start, start), as_of=date.today())
    assert report["summary"]["covered_sets"] == 3
    assert report["summary"]["on_time_workouts"] == 0
    with engine.connect() as connection:
        assert connection.execute(select(actual_exercises.c.exercise_id).where(actual_exercises.c.workout_exercise_id == 200)).scalar_one() == 2
    remove_exercise_match(engine, 2, target_id)
    assert not load_plan_adherence(engine, plan.plan_id, start, start).matches


def test_cannot_map_exercise_from_another_session(schedule_data):
    engine, _, _, _ = schedule_data
    data = linked_report(schedule_data)
    with pytest.raises(ValueError, match="linked session"):
        save_exercise_match(engine, 2, data.workouts[0].targets[0].plan_exercise_id, 300)


def test_unlinking_session_clears_approvals_but_keeps_recorded_exercises(schedule_data):
    engine, start, plan, _ = schedule_data
    data = linked_report(schedule_data)
    target_id = data.workouts[0].targets[0].plan_exercise_id
    save_exercise_match(engine, 2, target_id, 200)
    unassign_scheduled_session(engine, data.workouts[0].slot.day_id, start, 2)
    with engine.connect() as connection:
        assert connection.execute(select(matches)).all() == []
        assert len(connection.execute(select(actual_exercises)).all()) == 2


def test_same_recorded_exercise_cannot_be_approved_for_two_positions(schedule_data):
    engine, start, plan, _ = schedule_data
    seed_alternative(engine)
    other = save_training_plan(engine, replace(plan.draft, days=(TrainingDay("Upper", 0, (
        PlannedExercise(1, 3, 6, 10), PlannedExercise(1, 3, 10, 12),
    )),)))
    data = load_plan_adherence(engine, other.plan_id, start, start)
    assign_scheduled_session(engine, data.workouts[0].slot.day_id, start, 2)
    first, second = data.workouts[0].targets
    save_exercise_match(engine, 2, first.plan_exercise_id, 200)
    with pytest.raises(ValueError, match="another planned position"):
        save_exercise_match(engine, 2, second.plan_exercise_id, 200)
    assert len(load_plan_adherence(engine, other.plan_id, start, start).matches) == 1


APP = '''
import pandas as pd
import streamlit as st
from data_manager import DataManager
from ui.dashboard_view import DashboardView
from ui.plan_adherence_view import PlanAdherenceView
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
names = {1: "Barbell Bench Press", 2: "Machine Chest Press"}
month = st.session_state["test_month"]
if st.session_state.get("analysis"):
    PlanAdherenceView(manager=manager, exercise_names=names, selected_month=month).render()
else:
    frame = manager.load_sessions()
    frame["exercise_name"] = "Machine Chest Press"
    frame["repetitions"] = 8
    frame["weight"] = 50.
    frame["set_number"] = 1
    DashboardView({}, frame, month, data_manager=manager, exercise_names=names)._render_history()
'''


def test_approval_lives_in_analytics_and_can_be_removed(schedule_data):
    engine, start, plan, _ = schedule_data
    data = linked_report(schedule_data)
    target_id = data.workouts[0].targets[0].plan_exercise_id
    app = AppTest.from_string(APP, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["test_month"] = f"{start:%Y-%m}"
    app.run()
    app.button(key=f"history_date_{start}").click().run()
    assert not app.exception
    assert not app.dataframe
    assert not any(box.key.startswith("replacement_") for box in app.selectbox)
    app.session_state["analysis"] = True
    app.run()
    prefix = f"replacement_2_{target_id}"
    app.selectbox(key=f"{prefix}_exercise").select(200).run()
    app.button(key=f"{prefix}_confirm").click().run()
    assert not app.exception
    assert not app.error
    assert load_plan_adherence(engine, plan.plan_id, start, start).matches
    assert len(app.metric) == 3
    assert app.get("plotly_chart")
    app.button(key=f"{prefix}_remove").click().run()
    assert not app.exception
    assert not load_plan_adherence(engine, plan.plan_id, start, start).matches
