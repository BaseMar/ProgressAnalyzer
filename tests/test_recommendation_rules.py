"""Accepted training decisions, including equalization, corrections and deload."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from metrics.progression import recommend_normal_workout, recommend_workout
from models.set_load import SetLoad
from models.training_plan import PlannedExercise, ProgressionSettings
from test_plan_performance import data
from test_progression import upcoming, working

PLAN = PlannedExercise(1, 3, 8, 12, target_rir=2, weight_increment=2.5)
TODAY = date(2026, 11, 9)


def entry(
    weights=(60, 55, 55),
    reps=(12, 12, 12),
    rirs=(2, 2, 2),
    *,
    sid=1,
    day=TODAY - timedelta(days=7),
    planned=PLAN,
):
    workout, actual, match = working(sid, day, reps, planned=planned)
    return (
        workout,
        replace(
            actual,
            sets=tuple(replace(s, weight=w, rir=r) for s, w, r in zip(actual.sets, weights, rirs)),
        ),
        match,
    )


def normal(*entries, planned=PLAN):
    return recommend_normal_workout(data(*entries), upcoming(planned, day=TODAY), as_of=TODAY)[0]


@pytest.mark.parametrize(
    "weights,reps,action,expected",
    [
        ((60, 55, 55), (12, 12, 12), "equalize_weight", [(60, 12), (60, 8), (60, 8)]),
        ((60, 60, 55), (12, 12, 12), "equalize_weight", [(60, 12), (60, 12), (60, 8)]),
        ((60, 60, 60), (12, 8, 8), "increase_reps", [(60, 12), (60, 9), (60, 8)]),
        ((60, 55, 55), (12, 11, 12), "increase_reps", [(60, 12), (55, 12), (55, 12)]),
        ((60, 60, 60), (12, 12, 12), "increase_weight", [(62.5, 8)] * 3),
        ((60, 60, 60), (10, 9, 8), "increase_reps", [(60, 11), (60, 9), (60, 8)]),
        ((60, 60, 60), (13, 10, 10), "increase_reps", [(60, 12), (60, 11), (60, 10)]),
        ((60, 50, 50), (12, 12, 12), "equalize_weight", [(60, 12), (55, 8), (55, 8)]),
    ],
)
def test_accepted_progression_matrix(weights, reps, action, expected):
    source = entry(weights, reps)
    recommendation = normal(source)
    assert recommendation.action == action
    assert [(g.weight, g.minimum) for g in recommendation.goals] == expected
    assert recommendation.evidence_session_ids == (1,)
    assert recommendation.rules_version
    assert normal(source) == recommendation
    assert [s.weight for s in source[1].sets] == list(weights)


def test_low_reserve_blocks_equalization_without_reducing_a_twelve_rep_set():
    result = normal(entry(rirs=(2, 1, 2)))
    assert result.action == "maintain" and result.reason_code == "rir_below_target"
    assert [g.weight for g in result.goals] == [60, 55, 55]


def test_first_failure_at_minimum_reduces_only_that_set():
    result = normal(entry(weights=(60, 55, 55), reps=(12, 8, 10), rirs=(2, 0, 2)))
    assert result.action == "reduce_weight"
    assert [g.weight for g in result.goals] == [60, 52.5, 55]
    assert result.goals[1].minimum == 8


def test_large_equipment_step_never_creates_an_unavailable_setting():
    planned = replace(PLAN, weight_increment=5)
    result = normal(entry(weights=(60, 45, 45), planned=planned), planned=planned)
    assert result.reason_code == "weight_step_not_supported"
    assert [g.weight for g in result.goals] == [60, 45, 45]


def test_unknown_start_or_changed_prescription_is_manual():
    source = entry(weights=(40, 50, 50))
    assert normal(source).reason_code == "manual_start"
    assert not normal(source).goals
    changed = replace(PLAN, target_max=15)
    assert normal(entry(), planned=changed).reason_code == "manual_start"
    assert not normal(entry(), planned=changed).goals


def test_history_gap_uses_actual_date_and_does_not_invent_a_load():
    result = normal(entry(day=TODAY - timedelta(days=22)))
    assert result.reason_code == "history_gap" and not result.goals


def test_four_flat_exposures_flag_possible_plateau_and_cite_all_four():
    entries = [
        entry(
            weights=(60, 60, 60), reps=(10, 9, 8), sid=i + 1, day=TODAY - timedelta(days=21 - i * 7)
        )
        for i in range(4)
    ]
    result = normal(*entries)
    assert any("Possible plateau" in n for n in result.notices)
    assert result.evidence_session_ids == (1, 2, 3, 4)
    improving = (*entries[:3], entry(weights=(60, 60, 60), reps=(11, 9, 8), sid=4, day=TODAY))
    assert not any("Possible plateau" in n for n in normal(*improving).notices)


def test_confirmed_reserve_improvement_prevents_plateau_but_one_estimate_does_not():
    entries = [
        entry(
            weights=(60, 60, 60),
            reps=(10, 9, 8),
            sid=i + 1,
            day=TODAY - timedelta(days=21 - i * 7),
            rirs=(2, 2, 2) if i < 2 else (3, 3, 3),
        )
        for i in range(4)
    ]
    assert not any("Possible plateau" in n for n in normal(*entries).notices)
    first_three = [
        entry(
            weights=(60, 60, 60), reps=(10, 9, 8), sid=i + 1, day=TODAY - timedelta(days=21 - i * 7)
        )
        for i in range(3)
    ]
    assert any("Possible plateau" in n for n in normal(*first_three, entries[-1]).notices)


def test_time_adds_five_seconds_only_to_one_set_without_requiring_rir():
    planned = replace(PLAN, target_unit="seconds", target_min=30, target_max=60, target_rir=None)
    source = entry(weights=(0, 0, 0), reps=(60, 45, 40), rirs=(None, None, None), planned=planned)
    result = normal(source, planned=planned)
    assert result.action == "increase_time"
    assert [g.minimum for g in result.goals] == [60, 50, 40]
    assert result.target_rir is None


def test_bodyweight_progresses_repetitions_but_not_added_weight_or_assistance():
    source = entry(weights=(5, 5, 5), reps=(10, 9, 8))
    workout, actual, match = source
    source = (
        workout,
        replace(
            actual,
            sets=tuple(
                replace(s, load=SetLoad("assisted_bodyweight", 5, 80, 20)) for s in actual.sets
            ),
        ),
        match,
    )
    result = normal(source)
    assert result.action == "increase_reps"
    assert [g.minimum for g in result.goals] == [11, 9, 8]
    assert all(g.weight == 5 and g.assistance_kg == 20 for g in result.goals)


def test_legacy_bodyweight_never_becomes_a_future_total_mass_or_added_load():
    history = replace(
        data(entry(weights=(90.3,) * 3, reps=(10, 9, 8))), manual_load_exercise_ids=frozenset({1})
    )
    result = recommend_normal_workout(history, upcoming(PLAN, day=TODAY), as_of=TODAY)[0]
    assert result.action == "increase_reps"
    assert all(g.weight is None for g in result.goals)
    assert [s.weight for s in history.recorded[0].sets] == [90.3] * 3


def test_duplicate_recorded_exercise_needs_explicit_mapping_before_progression():
    history = data(entry(weights=(60,) * 3))
    actual = history.recorded[0]
    duplicate = replace(
        actual,
        workout_exercise_id=200,
        sets=tuple(replace(s, workout_exercise_id=200) for s in actual.sets),
    )
    history = replace(history, recorded=(actual, duplicate))
    result = recommend_normal_workout(history, upcoming(PLAN, day=TODAY), as_of=TODAY)[0]
    assert result.reason_code == "ambiguous_recorded_exercises" and not result.goals


def test_returning_to_an_old_exercise_does_not_bridge_a_different_exercise_in_the_same_position():
    first = replace(PLAN, history_key="stable-position")
    changed = replace(first, exercise_id=2)
    old = entry(weights=(60,) * 3, planned=first, day=TODAY - timedelta(days=14))
    other = working(2, TODAY - timedelta(days=7), (12, 12, 12), planned=changed, actual_id=2)
    result = normal(old, other, planned=first)
    assert result.reason_code == "manual_start" and not result.goals
    current = entry(weights=(60,) * 3, planned=first, sid=3, day=TODAY)
    assert normal(old, other, current, planned=first).action == "increase_weight"


def test_projected_unplanned_record_does_not_claim_the_future_positions_identity():
    planned = replace(PLAN, history_key="local-position")
    local = entry(weights=(60,) * 3, planned=planned, day=TODAY - timedelta(days=14))
    source_plan = replace(PLAN, exercise_id=2, history_key="another-position")
    extra = working(2, TODAY - timedelta(days=7), (12, 12, 12), planned=source_plan, actual_id=1)
    extra = (replace(extra[0], slot=replace(extra[0].slot, name="Other workout")), extra[1], None)
    result = normal(local, extra, planned=planned)
    assert result.action == "increase_weight" and result.evidence_session_ids == (1,)


def test_deload_keeps_all_sets_and_actual_repetitions_and_reduces_load_30_to_40_percent():
    source = entry(weights=(60, 55, 55), reps=(12, 10, 9), day=date(2026, 6, 8))
    result = recommend_workout(
        data(source),
        upcoming(PLAN, day=date(2026, 6, 15)),
        as_of=date(2026, 6, 15),
        settings=ProgressionSettings(date(2026, 5, 4), 7),
    ).exercises[0]
    assert result.action == "deload" and len(result.goals) == 3
    assert [g.minimum for g in result.goals] == [12, 10, 9]
    assert result.target_rir == 3 and result.target_rir_max == 4
    assert all(
        0.30 <= (old.weight - new.weight) / old.weight <= 0.40
        for old, new in zip(source[1].sets, result.goals)
    )
