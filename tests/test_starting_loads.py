"""Persist defaults without sharing them across unrelated training contexts."""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from db.starting_loads import load_starting_loads, save_starting_loads, starting_loads
from models.progression import ExerciseRecommendation, SetGoal, TrainingBlockPhase
from test_plan_schedule import schedule_data as schedule_data
from test_progression import upcoming


def choices():
    workout = upcoming()
    workout = replace(
        workout,
        targets=(
            replace(
                workout.targets[0],
                exercise=replace(workout.targets[0].exercise, history_key="plan:1:exercise:1"),
            ),
        ),
    )
    item = ExerciseRecommendation(
        101, 1, 1, workout.slot.scheduled_date, "insufficient_data", (), 2, "no_history", ""
    )
    phase = TrainingBlockPhase("normal", cycle_start=date(2026, 5, 4))
    goals = tuple(SetGoal(load, 6, 10, "reps", load_type="external") for load in (60.0, 55.0, 50.0))
    return workout, item, phase, goals


def test_per_set_loads_survive_another_date_and_save_can_update_them(schedule_data):
    engine = schedule_data[0]
    workout, item, phase, goals = choices()
    assert load_starting_loads(engine, workout, item, phase) == ()
    save_starting_loads(engine, workout, item, phase, goals)
    later = replace(
        workout,
        slot=replace(workout.slot, scheduled_date=workout.slot.scheduled_date + timedelta(days=7)),
    )
    later_item = replace(item, scheduled_date=later.slot.scheduled_date)
    assert load_starting_loads(engine, later, later_item, phase) == goals
    revised = (replace(goals[0], weight=57.5), *goals[1:])
    save_starting_loads(engine, later, later_item, phase, revised)
    assert load_starting_loads(engine, workout, item, phase) == revised
    with engine.connect() as connection:
        assert len(connection.execute(select(starting_loads)).all()) == 1


@pytest.mark.parametrize(
    "change",
    ["prescription", "plan_position", "alternative", "new_evidence", "cycle", "deload", "history"],
)
def test_saved_start_only_applies_to_its_manual_context(schedule_data, change):
    engine = schedule_data[0]
    workout, item, phase, goals = choices()
    save_starting_loads(engine, workout, item, phase, goals)
    if change in ("prescription", "plan_position"):
        exercise = workout.targets[0].exercise
        exercise = replace(
            exercise,
            **(
                {"target_rir": 3}
                if change == "prescription"
                else {"history_key": "another-position"}
            ),
        )
        workout = replace(workout, targets=(replace(workout.targets[0], exercise=exercise),))
    elif change == "alternative":
        item = replace(item, actual_exercise_id=2)
    elif change == "new_evidence":
        item = replace(item, evidence_session_ids=(2,), evidence_dates=(date(2026, 5, 18),))
    elif change == "cycle":
        phase = replace(phase, cycle_start=date(2026, 6, 22))
    elif change == "deload":
        phase = replace(phase, phase="deload")
    elif change == "history":
        item = replace(item, reason_code="upper_range_confirmed", action="increase_weight")
    assert load_starting_loads(engine, workout, item, phase) == ()


def test_zero_additional_load_and_assistance_are_persisted_explicitly(schedule_data):
    engine = schedule_data[0]
    workout, item, phase, _ = choices()
    goals = tuple(
        SetGoal(0.0, 6, 10, "reps", load_type="assisted_bodyweight", assistance_kg=load)
        for load in (20.0, 10.0, 0.0)
    )
    with pytest.raises(ValueError, match="every working set"):
        save_starting_loads(engine, workout, item, phase, goals[:2])
    with pytest.raises(ValueError, match="required assistance"):
        save_starting_loads(
            engine, workout, item, phase, (replace(goals[0], assistance_kg=None), *goals[1:])
        )
    save_starting_loads(engine, workout, item, phase, goals)
    assert load_starting_loads(engine, workout, item, phase) == goals
