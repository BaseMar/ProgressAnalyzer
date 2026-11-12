"""Recorded progress is independent of plan targets, links and history cutoffs."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, time
from itertools import chain

import pytest

from metrics.input import MetricsInput
from metrics.recorded_progress import compute_recorded_progress
from models.set_load import SetLoad
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet

AS_OF = date(2026, 11, 12)
FIRST, SECOND = date(2026, 10, 5), date(2026, 11, 10)


def entry(sid, day, values=(8, 8, 8), *, eid=1, weight=60.0, rir=1, **kwargs):
    wid = sid * 100 + eid
    return (
        WorkoutSession(sid, day, None, None),
        WorkoutExercise(wid, sid, eid),
        tuple(
            WorkoutSet(wid, number, value, weight, rir, **kwargs)
            for number, value in enumerate(values, 1)
        ),
    )


def data(*entries, deload=frozenset()):
    sessions = {item[0].session_id: item[0] for item in entries}
    return MetricsInput(
        list(sessions.values()),
        [item[1] for item in entries],
        list(chain.from_iterable(item[2] for item in entries)),
        [],
        [],
        [],
        [],
        [],
        deload,
    )


def report(*entries, **kwargs):
    return compute_recorded_progress(data(*entries), as_of=AS_OF, **kwargs)


def test_full_history_is_used_without_a_plan_link_target_or_21_day_cutoff():
    result = report(entry(1, FIRST), entry(2, SECOND, (9, 9, 9)), start=date(2026, 10, 16))
    assert result.exercise_progress.improving == 1
    insight = result.annotations[0]
    assert insight.code == "more_output"
    assert [source.session_id for source in insight.sources] == [1, 2]
    assert all(
        source.target_rir is None and source.planned_sets is None for source in insight.sources
    )
    assert all(source.scheduled_date is None for source in insight.sources)
    assert "05 Oct 2026" in insight.evidence and "10 Nov 2026" in insight.evidence
    assert "RIR 1/1/1" in insight.evidence
    with pytest.raises(FrozenInstanceError):
        insight.sources[0].sets[0].rir = 2


@pytest.mark.parametrize(
    "values,field,code",
    [
        ((9, 9, 9), "improving", "more_output"),
        ((8, 8, 8), "unchanged", "same_output"),
        ((7, 7, 7), "lower", "less_output"),
    ],
)
def test_actual_output_verdicts(values, field, code):
    result = report(entry(1, FIRST), entry(2, SECOND, values))
    assert getattr(result.exercise_progress, field) == 1
    assert result.annotations[0].code == code


@pytest.mark.parametrize(
    "options,code",
    [
        ({"weight": 65.0}, "load_changed"),
        ({"rir": 0}, "effort_changed"),
    ],
)
def test_changed_load_or_actual_reserve_is_not_graded_as_progress(options, code):
    result = report(entry(1, FIRST), entry(2, SECOND, (10, 10, 10), **options))
    assert result.exercise_progress.compared == 0
    assert result.exercise_progress.unassessed == 1
    assert result.annotations[0].code == code
    assert result.highlighted_annotations == ()


def test_matching_rir_averages_do_not_hide_changed_per_set_reserve():
    old = entry(1, FIRST)
    new = entry(2, SECOND, (10, 10, 10))
    old = (*old[:2], tuple(replace(s, rir=r) for s, r in zip(old[2], (1, 2, 3))))
    new = (*new[:2], tuple(replace(s, rir=r) for s, r in zip(new[2], (3, 2, 1))))
    assert report(old, new).annotations[0].code == "effort_changed"


@pytest.mark.parametrize(
    "latest,reason",
    [
        (entry(3, SECOND, rir=None), "missing RIR"),
        (entry(3, SECOND, values=()), "no recorded working sets"),
        (entry(3, SECOND, values=(10, 10)), "working set count changed"),
        (entry(3, SECOND, values=(float("nan"), 8, 8)), "invalid recorded values"),
        (entry(3, SECOND, weight=-1), "invalid recorded values"),
    ],
)
def test_incomplete_latest_log_never_falls_back_to_an_older_success(latest, reason):
    result = report(entry(1, FIRST), entry(2, date(2026, 10, 12), (9, 9, 9)), latest)
    assert result.exercise_progress.compared == 0
    assert result.exercise_progress.unassessed == 1
    assert reason in result.annotations[0].evidence
    assert not result.highlighted_annotations


def test_previous_incomplete_log_is_not_skipped():
    result = report(entry(1, FIRST), entry(2, date(2026, 10, 12), rir=None), entry(3, SECOND))
    assert result.exercise_progress.unassessed == 1
    assert "previous result: missing RIR" in result.annotations[0].evidence


def test_deload_does_not_get_an_ordinary_progress_verdict():
    entries = (entry(1, FIRST), entry(2, SECOND, (9, 9, 9)))
    for wid in (101, 201):
        result = compute_recorded_progress(data(*entries, deload=frozenset({wid})), as_of=AS_OF)
        assert result.exercise_progress.unassessed == 1
        assert "deload work" in result.annotations[0].evidence


def test_timed_work_uses_seconds_without_requiring_rir():
    old = entry(1, FIRST, (0, 0), rir=None, duration_seconds=30)
    new = entry(2, SECOND, (0, 0), rir=None, duration_seconds=40)
    result = report(old, new)
    assert result.exercise_progress.improving == 1
    assert "20 more seconds" in result.annotations[0].observation
    assert "RIR" not in result.annotations[0].evidence
    assert report(entry(1, FIRST), new).exercise_progress.unassessed == 1


@pytest.mark.parametrize(
    "old_load,new_load,reason",
    [
        (None, SetLoad("external", 60), "load convention changed"),
        (SetLoad("bodyweight", 0, None), SetLoad("bodyweight", 0, 80), "unknown body mass"),
        (
            SetLoad("assisted_bodyweight", 0, 80, None),
            SetLoad("assisted_bodyweight", 0, 80, 20),
            "unknown body mass",
        ),
    ],
)
def test_load_conventions_and_unknown_bodyweight_never_become_zero(old_load, new_load, reason):
    old = entry(1, FIRST, weight=old_load.external_weight_kg if old_load else 60, load=old_load)
    new = entry(2, SECOND, weight=new_load.external_weight_kg, load=new_load)
    result = report(old, new)
    assert result.exercise_progress.unassessed == 1
    assert reason in result.annotations[0].evidence


def test_changed_body_mass_is_a_load_change_even_with_no_added_weight():
    old = entry(1, FIRST, weight=0, load=SetLoad("bodyweight", 0, 80))
    new = entry(2, SECOND, (9, 9, 9), weight=0, load=SetLoad("bodyweight", 0, 82))
    result = report(old, new)
    assert result.exercise_progress.unassessed == 1
    assert result.annotations[0].code == "load_changed"


def test_warmups_are_excluded_and_explicit_working_labels_are_preserved():
    entries = []
    for sid, day, values in ((1, FIRST, (8, 8)), (2, SECOND, (9, 9))):
        session, exercise, sets = entry(sid, day, values, rir=5, is_warmup=False)
        warmup = WorkoutSet(exercise.workout_exercise_id, 1, 20, 20, 8, is_warmup=True)
        entries.append(
            (session, exercise, (warmup, *(replace(s, set_number=s.set_number + 1) for s in sets)))
        )
    result = report(*entries)
    assert result.exercise_progress.improving == 1
    assert len(result.annotations[0].sources[1].sets) == 2
    assert result.annotations[0].sources[1].excluded_kinds == ("warmup",)


def test_counts_and_highlights_include_all_latest_exercises_beyond_top_five():
    entries = [
        entry(sid, day, values, eid=eid)
        for eid in range(1, 9)
        for sid, day, values in ((1, FIRST, (8, 8, 8)), (2, SECOND, (8 + eid,) * 3))
    ]
    result = report(*reversed(entries))
    assert result.exercise_progress.improving == 8
    assert len(result.annotations) == 5
    assert result.omitted_annotations == 3
    assert result.highlighted_annotations[0].exercise_id == 8


def test_latest_actual_date_window_excludes_future_and_old_only_exercises():
    result = report(
        entry(1, FIRST),
        entry(2, SECOND, (9, 9, 9)),
        entry(3, date(2026, 11, 13), (1, 1, 1)),
        entry(4, FIRST, eid=2),
        start=date(2026, 10, 16),
    )
    assert result.exercise_progress.improving == 1
    assert result.exercise_progress.unassessed == 0
    assert report(entry(1, FIRST), entry(2, SECOND), end=FIRST).exercise_progress.unassessed == 1


def test_same_day_and_duplicate_exercise_entries_are_not_silently_combined():
    assert report(entry(1, SECOND), entry(2, SECOND)).exercise_progress.unassessed == 1
    old, new = entry(1, FIRST), entry(2, SECOND)
    duplicate = (new[0], replace(new[1], workout_exercise_id=999), (WorkoutSet(999, 1, 8, 60, 1),))
    result = report(old, new, duplicate)
    assert result.exercise_progress.unassessed == 1
    assert "multiple entries" in result.annotations[0].evidence


def test_session_times_order_records_deterministically_with_ids_as_tie_breaker():
    first = entry(1, FIRST)
    earlier = entry(9, SECOND, (9, 9, 9))
    latest = entry(2, SECOND, (10, 10, 10))
    latest = (replace(latest[0], start_time=time(20)), *latest[1:])
    result = report(latest, earlier, first)
    assert result.exercise_progress.unassessed == 1
    assert result.annotations[0].sources[-1].session_id == 2


def test_sqlite_string_dates_and_times_mix_with_postgres_time_objects():
    previous = entry(1, FIRST)
    earlier = entry(9, SECOND, (9, 9, 9))
    earlier = (replace(earlier[0], session_date="2026-11-10", start_time="10:00:00"), *earlier[1:])
    latest = entry(2, SECOND, (10, 10, 10))
    latest = (replace(latest[0], start_time=time(20)), *latest[1:])
    result = report(previous, latest, earlier)
    assert result.annotations[0].sources[-1].session_id == 2
