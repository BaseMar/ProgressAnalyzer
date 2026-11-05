"""Comparable plan executions, target checks and history across month filters."""

from dataclasses import replace
from datetime import date, time

from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from test_plan_schedule import schedule_data
from db.plan_adherence import actual_exercises, actual_sets, load_plan_performance
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.training_plans import save_training_plan
from metrics.plan_performance import compute_plan_performance
from models.plan_adherence import ExerciseMatch, PlanAdherenceInput, PlannedTarget, PlannedWorkout, RecordedExercise
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise
from models.workout_set import WorkoutSet

AS_OF = date(2026, 6, 1)


def execution(sid, day, values=(10, 9, 8), *, actual_id=1, weight=60., rir=2, planned=None):
    planned = planned or PlannedExercise(1, 3, 6, 10, target_rir=2)
    we_id = sid * 100
    sets = tuple(WorkoutSet(we_id, index + 1, value if planned.target_unit == "reps" else 0,
                           weight, rir, value if planned.target_unit == "seconds" else None)
                 for index, value in enumerate(values))
    return (
        PlannedWorkout(ScheduledWorkout(10, 1, day, "Upper A", sid, day), (PlannedTarget(101, planned),)),
        RecordedExercise(we_id, sid, actual_id, sets),
        ExerciseMatch(sid, 101, we_id) if actual_id != planned.exercise_id else None,
    )


def data(*entries, session_order=()):
    return PlanAdherenceInput(tuple(item[0] for item in entries), tuple(item[1] for item in entries),
                              tuple(item[2] for item in entries if item[2]), session_order)


def test_same_load_compares_reps_and_checks_range_and_rir():
    rows = compute_plan_performance(data(
        execution(1, date(2026, 5, 4)), execution(2, date(2026, 5, 11), (10, 10, 9)),
    ), as_of=AS_OF)
    assert rows[1]["reps_delta"] == 2
    assert rows[1]["comparison"] == "More reps at the same load"
    assert rows[1]["in_range"] == 3
    assert rows[1]["range_met"]
    assert rows[1]["rir_status"] == "At target"
    assert rows[1]["rir_delta"] == 0
    assert rows[1]["previous"]["session_id"] == 1


def test_range_boundaries_below_and_above_are_distinguished():
    row = compute_plan_performance(data(execution(1, date(2026, 5, 4), (5, 6, 11))), as_of=AS_OF)[0]
    assert (row["below_range"], row["in_range"], row["above_range"]) == (1, 1, 1)
    assert not row["range_met"]


def test_missing_rir_is_not_zero_and_target_zero_is_valid():
    rows = compute_plan_performance(data(
        execution(1, date(2026, 5, 4), rir=None), execution(2, date(2026, 5, 11), rir=0),
    ), as_of=AS_OF)
    assert rows[0]["avg_rir"] is None
    assert rows[0]["rir_status"] == "Incomplete RIR data"
    assert rows[1]["avg_rir"] == 0
    assert rows[1]["rir_delta"] is None
    assert rows[1]["rir_status"].startswith("Below target")
    zero = replace(PlannedExercise(1, 3, 6, 10), target_rir=0)
    assert compute_plan_performance(data(execution(1, date(2026, 5, 4), rir=0, planned=zero)), as_of=AS_OF)[0]["rir_status"] == "At target"


def test_load_change_shows_both_results_without_repetition_progress_label():
    row = compute_plan_performance(data(
        execution(1, date(2026, 5, 4)), execution(2, date(2026, 5, 11), (8, 8, 7), weight=65.),
    ), as_of=AS_OF)[1]
    assert row["reps_delta"] is None
    assert row["comparison"] == "Load changed: inspect individual sets"
    assert row["previous"]["sets"][0]["weight"] == 60
    assert row["sets"][0]["weight"] == 65


def test_incomplete_current_or_previous_execution_is_not_graded():
    rows = compute_plan_performance(data(
        execution(1, date(2026, 5, 4)), execution(2, date(2026, 5, 11), (10, 9)),
        execution(3, date(2026, 5, 18)),
    ), as_of=AS_OF)
    assert rows[1]["missing_sets"] == 1
    assert rows[1]["comparison"] == rows[2]["comparison"] == "Not comparable: incomplete set count"
    assert rows[2]["previous"]["session_id"] == 2
    assert rows[2]["reps_delta"] is None


def test_substitute_and_original_keep_separate_histories():
    rows = compute_plan_performance(data(
        execution(1, date(2026, 5, 4)),
        execution(2, date(2026, 5, 11), actual_id=2),
        execution(3, date(2026, 5, 18), (10, 10, 9), actual_id=2),
        execution(4, date(2026, 5, 25), (10, 10, 10)),
    ), as_of=AS_OF)
    assert rows[1]["previous"] is None
    assert rows[2]["previous"]["session_id"] == 2
    assert rows[2]["actual_exercise_id"] == 2
    assert rows[3]["previous"]["session_id"] == 1
    assert rows[3]["actual_exercise_id"] == 1


def test_target_change_starts_a_new_context_but_identical_new_version_does_not():
    first = execution(1, date(2026, 5, 4))
    second = execution(2, date(2026, 5, 11))
    second = (replace(second[0], slot=replace(second[0].slot, day_id=20, version_id=2),
                      targets=(replace(second[0].targets[0], plan_exercise_id=201),)), second[1], None)
    third = execution(3, date(2026, 5, 18), planned=PlannedExercise(1, 3, 8, 12, target_rir=2))
    rows = compute_plan_performance(data(first, second, third), as_of=AS_OF)
    assert rows[1]["previous"]["session_id"] == 1
    assert rows[2]["previous"] is None


def test_actual_dates_and_same_day_session_order_override_planned_dates():
    first = execution(1, date(2026, 5, 4))
    second = execution(2, date(2026, 5, 11))
    first = (replace(first[0], slot=replace(first[0].slot, performed_on=date(2026, 5, 12))), first[1], None)
    second = (replace(second[0], slot=replace(second[0].slot, performed_on=date(2026, 5, 5))), second[1], None)
    rows = compute_plan_performance(data(first, second), as_of=AS_OF)
    assert [row["session_id"] for row in rows] == [2, 1]
    assert rows[1]["previous"]["session_id"] == 2
    second = (replace(second[0], slot=replace(second[0].slot, performed_on=date(2026, 5, 12))), second[1], None)
    rows = compute_plan_performance(data(first, second, session_order=(2, 1)), as_of=AS_OF)
    assert rows[1]["previous"]["session_id"] == 2


def test_timed_exercises_compare_seconds_at_same_load():
    planned = PlannedExercise(1, 2, 45, 60, "seconds")
    row = compute_plan_performance(data(
        execution(1, date(2026, 5, 4), (45, 45), weight=0, planned=planned),
        execution(2, date(2026, 5, 11), (60, 50), weight=0, planned=planned),
    ), as_of=AS_OF)[1]
    assert row["seconds_delta"] == 20
    assert row["reps_delta"] is None
    assert row["range_met"]
    assert row["rir_status"] == "Not specified"


def test_month_filter_preserves_previous_execution_outside_visible_month():
    rows = compute_plan_performance(data(
        execution(1, date(2026, 4, 27)), execution(2, date(2026, 5, 4)),
    ), as_of=AS_OF, start=date(2026, 5, 1), end=date(2026, 5, 31))
    assert len(rows) == 1
    assert rows[0]["previous"]["performed_on"] == date(2026, 4, 27)


def seed_history(schedule_data):
    engine, _, source, sessions = schedule_data
    start = date(2024, 4, 29)
    current = date(2024, 5, 6)
    plan = save_training_plan(engine, replace(source.draft, effective_from=start))
    slots = load_scheduled_workouts(engine, plan.plan_id, start, current)
    assign_scheduled_session(engine, slots[0].day_id, start, 2)
    assign_scheduled_session(engine, slots[-1].day_id, current, 3)
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=start, start_time=time(18)))
        connection.execute(sessions.update().where(sessions.c.session_id == 3).values(session_date=current, start_time=time(8)))
        connection.execute(actual_exercises.insert(), [
            {"workout_exercise_id": 700, "session_id": 2, "exercise_id": 1},
            {"workout_exercise_id": 800, "session_id": 3, "exercise_id": 1},
        ])
        connection.execute(actual_sets.insert(), [
            {"workout_exercise_id": we_id, "set_number": number, "repetitions": 8 if we_id == 700 else 9,
             "weight": 60., "rir": 2, "duration_seconds": None}
            for we_id in (700, 800) for number in (1, 2, 3)
        ])
    return plan, start, current


def test_database_loader_includes_earlier_month_and_orders_same_day_times(schedule_data):
    engine, _, _, sessions = schedule_data
    plan, start, current = seed_history(schedule_data)
    history = load_plan_performance(engine, plan.plan_id, date(2024, 5, 1), date(2024, 5, 31))
    rows = compute_plan_performance(history, as_of=AS_OF, start=date(2024, 5, 1), end=date(2024, 5, 31))
    row = next(item for item in rows if item["session_id"] == 3)
    assert row["previous"]["session_id"] == 2
    with engine.begin() as connection:
        connection.execute(sessions.update().where(sessions.c.session_id == 2).values(session_date=current))
    history = load_plan_performance(engine, plan.plan_id, start, current)
    assert history.session_order == (3, 2)


def test_analytics_displays_previous_month_result_and_target_checks(schedule_data):
    engine, _, _, _ = schedule_data
    plan, _, _ = seed_history(schedule_data)
    app = AppTest.from_string('''
import streamlit as st
from data_manager import DataManager
from ui.plan_adherence_view import PlanAdherenceView
manager = object.__new__(DataManager)
manager.engine = st.session_state["test_engine"]
PlanAdherenceView(manager=manager, exercise_names={1: "Bench Press"}, selected_month="2024-05").render(mode="exercise")
''', default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["adherence_plan"] = plan.plan_id
    app.run()
    assert not app.exception
    assert not app.error
    assert not app.metric
    assert len(app.get("plotly_chart")) == 1
    tables = [table.value for table in app.dataframe]
    comparison_table = next(table for table in tables if "Previous" in table.columns)
    assert "8 reps @ 60 kg" in comparison_table.iloc[0]["Previous"]
    assert "9 reps @ 60 kg" in comparison_table.iloc[0]["Current"]
    assert any("3/3 sets in range" in item.value for item in app.caption)
    assert any("More reps at the same load" in item.value for item in app.markdown)
