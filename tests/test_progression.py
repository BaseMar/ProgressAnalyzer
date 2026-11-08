"""Explainable next-session rules, no writes and no deload/UI integration."""
from dataclasses import FrozenInstanceError, replace
from datetime import date, time

import pytest
from sqlalchemy import func, select

from test_plan_performance import execution, data
from test_plan_schedule import schedule_data
from db.plan_adherence import actual_exercises, actual_sets
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.progression import load_normal_workout_recommendations
from db.training_plans import save_training_plan
from metrics.progression import recommend_normal_workout
from models.plan_adherence import PlannedTarget, PlannedWorkout
from models.progression import ProgressionPolicy
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise, ProgressionSettings
from models.workout_set import WorkoutSet

AS_OF = date(2026, 5, 20)
BLOCK = date(2026, 5, 1)
PLAN = PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5)


def working(sid, day, values=(10, 10, 9), *, actual_id=1, weight=60., rir=2, planned=PLAN):
    workout, actual, match = execution(sid, day, values, actual_id=actual_id, weight=weight, rir=rir, planned=planned)
    actual = replace(actual, sets=tuple(replace(item, is_warmup=False) for item in actual.sets))
    return workout, actual, match


def upcoming(planned=PLAN, *, day=date(2026, 5, 25)):
    return PlannedWorkout(ScheduledWorkout(10, 1, day, "Upper A"), (PlannedTarget(101, planned),))


def recommend(*entries, target=None, **options):
    return recommend_normal_workout(data(*entries), target or upcoming(), as_of=AS_OF, block_start=BLOCK, **options)[0]


def test_adds_one_total_rep_to_lowest_set_and_preserves_inputs():
    entry = working(1, date(2026, 5, 18))
    result = recommend(entry)
    assert result.action == "increase_reps"
    assert [(item.weight, item.minimum, item.maximum) for item in result.goals] == [(60., 10, 10)] * 3
    assert result.target_rir == 2
    assert result.evidence_session_ids == (1,)
    assert entry[1].sets[-1].repetitions == 9
    with pytest.raises(FrozenInstanceError):
        result.action = "maintain"


def test_first_set_below_ceiling_gets_the_additional_rep():
    result = recommend(working(1, date(2026, 5, 18), (8, 7, 7)))
    assert [item.minimum for item in result.goals] == [9, 7, 7]


def test_two_top_executions_increase_one_hardware_step_and_target_lower_bound():
    result = recommend(working(1, date(2026, 5, 11), (10, 10, 10)), working(2, date(2026, 5, 18), (10, 10, 10)))
    assert result.action == "increase_weight"
    assert [(item.weight, item.minimum, item.maximum) for item in result.goals] == [(62.5, 6, 6)] * 3
    assert result.evidence_session_ids == (2,)


def test_one_complete_top_execution_is_sufficient():
    result = recommend(working(1, date(2026, 5, 18), (10, 10, 10)))
    assert (result.action, result.reason_code) == ("increase_weight", "upper_range_confirmed")
    assert [(item.weight, item.minimum) for item in result.goals] == [(62.5, 6)] * 3


def test_rir_target_is_a_minimum_reserve_and_zero_remains_zero():
    assert recommend(working(1, date(2026, 5, 18), rir=3)).action == "increase_reps"
    assert recommend(working(1, date(2026, 5, 18), rir=0)).reason_code == "rir_below_target"


def test_confirmation_policy_can_require_three_exposures():
    history = tuple(working(index, date(2026, 5, day), (10, 10, 10)) for index, day in enumerate((4, 11, 18), 1))
    policy = ProgressionPolicy(confirmations_required=3)
    assert recommend(*history[1:], policy=policy).reason_code == "confirm_upper_range"
    assert recommend(*history, policy=policy).action == "increase_weight"


@pytest.mark.parametrize("values", [
    {"confirmations_required": 0}, {"max_history_gap_days": 0},
    {"max_relative_weight_increase": float("nan")}, {"max_relative_weight_increase": None},
])
def test_invalid_policy_is_rejected(values):
    with pytest.raises(ValueError):
        ProgressionPolicy(**values)


@pytest.mark.parametrize("problem, code", [
    ("partial", "incomplete_sets"),
    ("missing_rir", "missing_rir"), ("target_rir", "missing_target_rir"),
])
def test_incomplete_or_unknown_evidence_does_not_produce_numeric_increases(problem, code):
    planned = replace(PLAN, target_rir=None) if problem == "target_rir" else PLAN
    entry = working(1, date(2026, 5, 18), planned=planned)
    if problem == "partial":
        entry = (entry[0], replace(entry[1], sets=entry[1].sets[:2]), entry[2])
    if problem == "missing_rir":
        change = {"rir": None}
        entry = (entry[0], replace(entry[1], sets=(replace(entry[1].sets[0], **change), *entry[1].sets[1:])), entry[2])
    result = recommend(entry, target=upcoming(planned))
    assert result.action == "insufficient_data"
    assert result.reason_code == code
    assert result.goals == ()


def test_one_low_rir_set_blocks_increase_even_when_mean_equals_target():
    entry = working(1, date(2026, 5, 18))
    entry = (entry[0], replace(entry[1], sets=tuple(replace(item, rir=rir) for item, rir in zip(entry[1].sets, (0, 3, 3)))), entry[2])
    result = recommend(entry)
    assert result.reason_code == "rir_below_target"
    assert result.action == "maintain"
    assert all((item.minimum, item.maximum) == (6, 10) for item in result.goals)


def test_below_minimum_corrects_load_and_excess_reps_are_capped():
    assert recommend(working(1, date(2026, 5, 18), (5, 8, 8))).reason_code == "minimum_not_met"
    result = recommend(working(1, date(2026, 5, 18), (11, 9, 9)))
    assert result.reason_code == "one_more_rep"
    assert [g.minimum for g in result.goals] == [10, 10, 9]


def test_prior_partial_or_changed_load_does_not_override_the_latest_complete_success():
    latest = working(2, date(2026, 5, 18), (10, 10, 10))
    assert recommend(working(1, date(2026, 5, 11), (10, 10)), latest).reason_code == "upper_range_confirmed"
    assert recommend(working(1, date(2026, 5, 11), (10, 10, 10), weight=55.), latest).reason_code == "upper_range_confirmed"


def test_ascending_trials_require_manual_working_start():
    entry = working(1, date(2026, 5, 18))
    entry = (entry[0], replace(entry[1], sets=(entry[1].sets[0], replace(entry[1].sets[1], weight=65), entry[1].sets[2])), entry[2])
    result = recommend(entry)
    assert result.reason_code == "manual_start"
    assert not result.goals


def test_large_step_is_not_rounded_to_an_unavailable_load():
    planned = replace(PLAN, weight_increment=20.)
    result = recommend(working(1, date(2026, 5, 11), (10, 10, 10), planned=planned),
                       working(2, date(2026, 5, 18), (10, 10, 10), planned=planned), target=upcoming(planned))
    assert result.action == "maintain"
    assert result.reason_code == "weight_step_not_supported"
    assert all(item.weight == 60 for item in result.goals)


def test_missing_weight_step_does_not_invent_one():
    planned = replace(PLAN, weight_increment=None)
    result = recommend(working(1, date(2026, 5, 11), (10, 10, 10), planned=planned),
                       working(2, date(2026, 5, 18), (10, 10, 10), planned=planned), target=upcoming(planned))
    assert result.reason_code == "missing_weight_step"
    assert not result.goals


def test_decimal_load_addition_has_no_binary_artifact():
    planned = replace(PLAN, weight_increment=.2)
    result = recommend(working(1, date(2026, 5, 11), (10, 10, 10), planned=planned, weight=12.1),
                       working(2, date(2026, 5, 18), (10, 10, 10), planned=planned, weight=12.1), target=upcoming(planned))
    assert result.goals[0].weight == 12.3


def test_warmup_cannot_manufacture_a_top_result_or_change_the_goal():
    entry = working(1, date(2026, 5, 18))
    warmup = WorkoutSet(100, 0, 50, 1000., 0, is_warmup=True)
    with_warmup = (entry[0], replace(entry[1], sets=(warmup, *entry[1].sets)), entry[2])
    assert recommend(with_warmup) == recommend(entry)


def test_last_linked_session_with_no_matching_sets_does_not_fall_back_to_older_success():
    first = working(1, date(2026, 5, 11), (10, 10, 10))
    last = working(2, date(2026, 5, 18))
    last = (last[0], replace(last[1], sets=()), last[2])
    assert recommend(first, last).reason_code == "incomplete_sets"


def test_unselected_replacement_never_becomes_the_next_original_exercise():
    substitute = working(1, date(2026, 5, 18), actual_id=2)
    assert recommend(substitute).reason_code == "no_history"
    selected = recommend(substitute, substitutions={101: 2})
    assert selected.action == "increase_reps"
    assert selected.actual_exercise_id == 2
    assert selected.planned_exercise_id == 1


def test_replacement_weight_step_is_not_copied_from_the_original():
    history = (working(1, date(2026, 5, 11), (10, 10, 10), actual_id=2),
               working(2, date(2026, 5, 18), (10, 10, 10), actual_id=2))
    assert recommend(*history, substitutions={101: 2}).reason_code == "missing_weight_step"
    result = recommend(*history, substitutions={101: 2}, replacement_weight_steps={2: 5.})
    assert result.action == "increase_weight"
    assert result.goals[0].weight == 65


def test_new_context_and_new_block_do_not_reuse_old_confirmations():
    entries = (working(1, date(2026, 5, 11), (10, 10, 10)), working(2, date(2026, 5, 18), (10, 10, 10)))
    result = recommend_normal_workout(data(*entries), upcoming(), as_of=AS_OF, block_start=date(2026, 5, 15))[0]
    assert result.reason_code == "upper_range_confirmed"
    changed = replace(PLAN, target_max=12)
    changed_result = recommend(*entries, target=upcoming(changed))
    assert changed_result.reason_code == "manual_start"
    assert changed_result.action == "insufficient_data"
    assert not changed_result.goals


def test_long_gap_and_same_day_confirmations_do_not_increase_load():
    old = working(1, date(2026, 5, 4))
    assert recommend(old, target=upcoming(day=date(2026, 6, 1))).reason_code == "history_gap"
    first = working(1, date(2026, 5, 11), (10, 10, 10))
    second = working(2, date(2026, 5, 18), (10, 10, 10))
    first = (replace(first[0], slot=replace(first[0].slot, performed_on=date(2026, 5, 18))), first[1], first[2])
    assert recommend(first, second).reason_code == "upper_range_confirmed"


def test_future_recorded_result_does_not_leak_into_recommendation():
    known = working(1, date(2026, 5, 11), (8, 8, 8))
    future = working(2, date(2026, 5, 18), (10, 10, 10))
    future = (replace(future[0], slot=replace(future[0].slot, performed_on=date(2026, 5, 22))), future[1], future[2])
    result = recommend(known, future)
    assert result.action == "increase_reps"
    assert result.evidence_session_ids == (1,)


def test_no_block_past_goal_and_already_recorded_are_explicit():
    empty = data()
    assert recommend_normal_workout(empty, upcoming(), as_of=AS_OF, block_start=None)[0].reason_code == "no_history"
    assert recommend_normal_workout(empty, upcoming(), as_of=AS_OF, block_start=date(2026, 6, 1))[0].reason_code == "before_block"
    with pytest.raises(ValueError, match="in the past"):
        recommend_normal_workout(empty, upcoming(day=date(2026, 5, 18)), as_of=AS_OF, block_start=BLOCK)
    recorded = replace(upcoming(), slot=replace(upcoming().slot, session_id=9, performed_on=AS_OF))
    assert recommend(target=recorded).reason_code == "already_recorded"


def test_timed_and_zero_load_exercises_do_not_get_implicit_weight_progression():
    timed = PlannedExercise(1, 3, 30, 60, "seconds", target_rir=2)
    assert recommend(working(1, date(2026, 5, 18), (60, 60, 60), planned=timed, weight=0), target=upcoming(timed)).reason_code == "time_ceiling_manual"
    assert recommend(working(1, date(2026, 5, 11), (10, 10, 10), weight=0),
                     working(2, date(2026, 5, 18), (10, 10, 10), weight=0)).reason_code == "zero_load"


def test_readonly_database_service_loads_prior_month_and_returns_goals(schedule_data):
    engine, _, source, sessions = schedule_data
    origin, first_day, second_day, next_day = date(2024, 4, 29), date(2024, 4, 29), date(2024, 5, 6), date(2024, 5, 13)
    plan = save_training_plan(engine, replace(source.draft, effective_from=origin,
        days=(replace(source.draft.days[0], name="Upper A", exercises=(PLAN,)),), progression=ProgressionSettings(origin, 7)))
    slots = load_scheduled_workouts(engine, plan.plan_id, first_day, next_day)
    with engine.begin() as connection:
        for sid, day in ((2, first_day), (3, second_day)):
            connection.execute(sessions.update().where(sessions.c.session_id == sid).values(session_date=day, start_time=time(8)))
        connection.execute(actual_exercises.insert(), [{"workout_exercise_id": sid * 100, "session_id": sid, "exercise_id": 1} for sid in (2, 3)])
        connection.execute(actual_sets.insert(), [{"set_id": sid * 10 + number, "workout_exercise_id": sid * 100,
            "set_number": number, "repetitions": 10, "weight": 60., "rir": 2, "duration_seconds": None}
            for sid in (2, 3) for number in (1, 2, 3)])
        from db.set_classifications import classifications
        connection.execute(classifications.insert(), [{"set_id": sid * 10 + number, "is_warmup": False} for sid in (2, 3) for number in (1, 2, 3)])
    assign_scheduled_session(engine, slots[0].day_id, first_day, 2)
    assign_scheduled_session(engine, slots[1].day_id, second_day, 3)
    with engine.connect() as connection:
        before = connection.execute(select(actual_sets)).mappings().all()
    result = load_normal_workout_recommendations(engine, plan.plan_id, slots[2].day_id, next_day, as_of=date(2024, 5, 7))[0]
    assert result.action == "increase_weight"
    assert result.goals[0].weight == 62.5
    assert result.evidence_session_ids == (3,)
    with engine.connect() as connection:
        assert connection.execute(select(actual_sets)).mappings().all() == before
    with pytest.raises(ValueError, match="not scheduled"):
        load_normal_workout_recommendations(engine, plan.plan_id, 9999, next_day, as_of=date(2024, 5, 7))
