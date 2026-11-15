"""Recurring plan deviations preserve context, observation windows and unknowns."""

from dataclasses import replace
from datetime import date, timedelta

import pytest
from streamlit.testing.v1 import AppTest

from db.plan_adherence import actual_exercises, actual_sets
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from metrics.plan_patterns import summarize_recurring_deviations
from metrics.plan_performance import compute_plan_performance
from models.training_plan import PlannedExercise, ProgressionSettings
from models.workout_set import WorkoutSet
from test_plan_performance import AS_OF, data, execution
from test_plan_schedule import schedule_data as schedule_data


def logs(*values, rir=2, planned=None):
    return data(
        *(
            execution(
                sid,
                date(2026, 5, 4) + timedelta(days=7 * (sid - 1)),
                reps,
                rir=rir,
                planned=planned,
            )
            for sid, reps in enumerate(values, 1)
        )
    )


def patterns(recorded, *, settings=None, start=None, end=None):
    rows = compute_plan_performance(
        recorded, as_of=AS_OF, start=start, end=end, settings_by_version=settings
    )
    return summarize_recurring_deviations(rows, as_of=AS_OF, settings_by_version=settings)


def by_code(report, code):
    return next(item for item in report["patterns"] if item["code"] == code)


@pytest.mark.parametrize(
    "values,code",
    [((5, 8, 8), "below_range"), ((11, 8, 8), "above_range"), ((8, 8), "incomplete_sets")],
)
def test_repeated_mismatches_have_assessed_counts_and_actual_source_dates(values, code):
    report = patterns(logs(values, (8, 8, 8), values, (8, 8, 8)))
    item = by_code(report, code)
    assert (item["occurrences"], item["assessed"], item["window_size"]) == (2, 4, 4)
    assert item["last_seen"] == date(2026, 5, 18)
    assert item["evidence"] == (
        (1, date(2026, 5, 4), True),
        (2, date(2026, 5, 11), False),
        (3, date(2026, 5, 18), True),
        (4, date(2026, 5, 25), False),
    )
    assert len(report["patterns"]) == 1


def test_one_mismatch_and_only_two_assessable_workouts_do_not_establish_a_pattern():
    assert not patterns(logs((5, 8, 8), (5, 8, 8)))["patterns"]
    result = patterns(logs((5, 8, 8), (8, 8, 8), (8, 8, 8)))
    assert not result["patterns"] and result["assessed_contexts"] == 1


def test_rir_is_checked_per_set_without_hiding_a_violation_behind_its_average():
    recorded = logs((8, 8, 8), (8, 8, 8), (8, 8, 8))
    recorded = replace(
        recorded,
        recorded=tuple(
            replace(item, sets=tuple(replace(s, rir=r) for s, r in zip(item.sets, (0, 3, 3))))
            for item in recorded.recorded
        ),
    )
    item = by_code(patterns(recorded), "below_target_rir")
    assert (item["occurrences"], item["assessed"]) == (3, 3)
    assert item["target_rir"] == 2


def test_unknown_rir_does_not_become_failure_but_quantities_can_still_be_assessed():
    report = patterns(logs((5, 8, 8), (5, 8, 8), (8, 8, 8), rir=None))
    assert [item["code"] for item in report["patterns"]] == ["below_range"]
    assert by_code(report, "below_range")["occurrences"] == 2
    zero = PlannedExercise(1, 3, 6, 10, target_rir=0)
    assert not patterns(logs((8, 8, 8), (8, 8, 8), (8, 8, 8), rir=0, planned=zero))["patterns"]


def test_incomplete_log_cannot_establish_that_all_sets_were_within_range_or_reserve():
    report = patterns(logs((5, 8, 8), (5, 8, 8), (8, 8), (8, 8, 8)))
    item = by_code(report, "below_range")
    assert (item["occurrences"], item["assessed"], item["window_size"]) == (2, 3, 4)
    assert item["evidence"][2][2] is None


def test_recent_window_does_not_replace_an_ambiguous_latest_log_with_older_evidence():
    rows = compute_plan_performance(logs((5, 8, 8), (5, 8, 8), (8, 8, 8), (8, 8, 8)), as_of=AS_OF)
    rows.append(dict(rows[-1], session_id=5, performed_on=AS_OF, ambiguous_recorded_exercises=True))
    result = summarize_recurring_deviations(rows, as_of=AS_OF)
    assert not result["patterns"]  # Last four: one mismatch, two successes, one unknown.


def test_warmups_do_not_create_an_incomplete_log_and_light_only_logs_remain_unknown():
    recorded = logs((8, 8, 8), (8, 8, 8), (8, 8, 8))
    with_warmups = replace(
        recorded,
        recorded=tuple(
            replace(
                item,
                sets=(
                    WorkoutSet(item.workout_exercise_id, 1, 12, 20, 8, is_warmup=True),
                    *(replace(s, set_number=s.set_number + 1) for s in item.sets),
                ),
            )
            for item in recorded.recorded
        ),
    )
    assert not patterns(with_warmups)["patterns"]
    report = patterns(logs((8, 8, 8), (8, 8, 8), (8, 8, 8), rir=5))
    assert not report["patterns"] and report["pending_contexts"] == 1


def test_unlinked_future_and_deload_rows_do_not_establish_a_pattern():
    rows = compute_plan_performance(logs((5, 8, 8), (5, 8, 8), (5, 8, 8)), as_of=AS_OF)
    for changes in (
        {"session_id": None},
        {"performed_on": AS_OF + timedelta(days=1)},
        {"training_phase": "deload"},
        {"performed_on": None},
    ):
        changed = [*rows[:2], dict(rows[2], **changes)]
        assert not summarize_recurring_deviations(changed, as_of=AS_OF)["patterns"]


def test_same_day_logs_count_once_and_keep_the_latest_execution():
    rows = compute_plan_performance(logs((5, 8, 8), (5, 8, 8), (5, 8, 8)), as_of=AS_OF)
    same_day = [dict(row, performed_on=date(2026, 5, 4)) for row in rows]
    result = summarize_recurring_deviations(same_day, as_of=AS_OF)
    assert not result["patterns"] and result["pending_contexts"] == 1
    good = compute_plan_performance(logs((8, 8, 8)), as_of=AS_OF)[0]
    rows.append(dict(good, performed_on=rows[-1]["performed_on"], session_id=99))
    item = by_code(summarize_recurring_deviations(rows, as_of=AS_OF), "below_range")
    assert item["evidence"][-1] == (99, date(2026, 5, 18), False)


def test_changed_targets_reset_the_segment_even_when_an_old_prescription_returns():
    old = PlannedExercise(1, 3, 6, 10, target_rir=2, history_key="bench-position")
    changed = replace(old, target_min=8, target_max=12)
    entries = [
        execution(sid, date(2026, 5, 4) + timedelta(days=3 * (sid - 1)), (5, 5, 5), planned=planned)
        for sid, planned in enumerate((old, old, old, changed, changed, old), 1)
    ]
    result = patterns(data(*entries))
    assert not result["patterns"] and result["pending_contexts"] == 1


def test_identical_revisions_keep_history_and_block_setting_changes_reset_it():
    rows = compute_plan_performance(logs((5, 8, 8), (5, 8, 8), (5, 8, 8), (5, 8, 8)), as_of=AS_OF)
    rows[-1] = dict(rows[-1], version_id=2, plan_exercise_id=202)
    first = ProgressionSettings(date(2026, 5, 1), 7)
    settings = {1: first, 2: first}
    item = by_code(
        summarize_recurring_deviations(rows, as_of=AS_OF, settings_by_version=settings),
        "below_range",
    )
    assert item["assessed"] == 4
    settings[2] = ProgressionSettings(date(2026, 5, 22), 7)
    assert not summarize_recurring_deviations(rows, as_of=AS_OF, settings_by_version=settings)[
        "patterns"
    ]


def test_replacements_and_repeated_positions_keep_separate_histories():
    entries = [
        execution(
            sid,
            date(2026, 5, 4) + timedelta(days=7 * (sid - 1)),
            (5, 5, 5),
            actual_id=1 if sid % 2 else 2,
        )
        for sid in range(1, 5)
    ]
    assert not patterns(data(*entries))["patterns"]
    rows = compute_plan_performance(logs((5, 8, 8), (5, 8, 8), (5, 8, 8)), as_of=AS_OF)
    copies = [dict(row, context=(*row["context"][:3], 2, *row["context"][4:])) for row in rows]
    result = summarize_recurring_deviations([*rows, *copies], as_of=AS_OF)
    assert {item["position"] for item in result["patterns"]} == {1, 2}
    assert all(item["assessed"] == 3 for item in result["patterns"])


def test_timed_targets_use_seconds_without_requiring_rir():
    planned = PlannedExercise(1, 2, 30, 60, "seconds")
    report = patterns(logs((25, 40), (25, 40), (40, 40), rir=None, planned=planned))
    item = by_code(report, "below_range")
    assert (item["unit"], item["occurrences"], item["assessed"]) == ("seconds", 2, 3)
    assert len(report["patterns"]) == 1


def test_selected_month_does_not_pull_in_older_mismatches_to_fill_the_window():
    recorded = logs((5, 8, 8), (5, 8, 8), (5, 8, 8), (5, 8, 8))
    report = patterns(recorded, start=date(2026, 5, 15), end=date(2026, 5, 31))
    assert not report["patterns"] and report["pending_contexts"] == 1


def test_load_changes_do_not_hide_observed_range_mismatches():
    entries = [
        execution(
            sid, date(2026, 5, 4) + timedelta(days=7 * (sid - 1)), (5, 8, 8), weight=60 + sid * 5
        )
        for sid in range(1, 4)
    ]
    assert by_code(patterns(data(*entries)), "below_range")["occurrences"] == 3


def test_table_is_compact_and_distinguishes_an_empty_assessment_from_no_pattern():
    report = patterns(logs((5, 8, 8), (5, 8, 8), (8, 8, 8)))
    app = AppTest.from_string("""
import streamlit as st
from ui.plan_adherence_view import PlanAdherenceView
PlanAdherenceView(manager=object(), exercise_names={1: 'Bench Press'}).render_recurring_deviations(
    st.session_state['report']
)
""")
    app.session_state["report"] = report
    app.run()
    assert not app.exception and not app.error
    table = app.dataframe[0].value
    assert list(table.columns) == [
        "Exercise",
        "Workout",
        "Deviation",
        "Occurrences / assessed",
        "Last seen",
    ]
    assert list(table.iloc[0]) == [
        "Bench Press",
        "Upper A · position 1",
        "Below 6–10 reps",
        "2/3",
        date(2026, 5, 11),
    ]
    assert not app.selectbox and not app.button and not app.caption
    app.session_state["report"] = patterns(logs((8, 8, 8), (8, 8, 8), (8, 8, 8)))
    app.run()
    assert not app.dataframe and app.info[0].value == "No repeated deviations in recent workouts."
    app.session_state["report"] = patterns(logs((5, 8, 8), (5, 8, 8)))
    app.run()
    assert not app.dataframe and "At least three" in app.info[0].value


def test_reordered_position_with_a_stable_history_key_starts_a_new_segment():
    planned = PlannedExercise(1, 3, 6, 10, target_rir=2, history_key="stable-bench")
    rows = compute_plan_performance(
        logs((5, 8, 8), (5, 8, 8), (5, 8, 8), planned=planned), as_of=AS_OF
    )
    rows[-1] = dict(rows[-1], context=(*rows[-1]["context"][:3], 2, *rows[-1]["context"][4:]))
    report = summarize_recurring_deviations(rows, as_of=AS_OF)
    assert not report["patterns"] and report["pending_contexts"] == 1


def test_sqlite_plan_consistency_renders_patterns_below_chart_and_respects_period(schedule_data):
    engine, start, plan, sessions = schedule_data
    session_ids = (2, 3, 1)
    with engine.begin() as connection:
        for index, sid in enumerate(session_ids):
            connection.execute(
                sessions.update()
                .where(sessions.c.session_id == sid)
                .values(session_date=start + timedelta(days=index * 7 + 1))
            )
        connection.execute(
            actual_exercises.insert(),
            [
                {"workout_exercise_id": sid * 100, "session_id": sid, "exercise_id": 1}
                for sid in session_ids
            ],
        )
        connection.execute(
            actual_sets.insert(),
            [
                {
                    "workout_exercise_id": sid * 100,
                    "set_number": number,
                    "repetitions": 5 if number == 3 else 8,
                    "weight": 60.0,
                    "rir": 2,
                    "duration_seconds": None,
                }
                for sid in session_ids
                for number in (1, 2, 3)
            ],
        )
    slots = load_scheduled_workouts(engine, plan.plan_id, start, start + timedelta(days=14))
    for slot, sid in zip(slots, session_ids):
        assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, sid)
    app = AppTest.from_string(
        """
import streamlit as st
from data_manager import DataManager
from ui.plan_adherence_view import PlanAdherenceView
manager = object.__new__(DataManager)
manager.engine = st.session_state['engine']
PlanAdherenceView(manager=manager, exercise_names={1: 'Bench Press'},
                  selected_month=st.session_state['month']).render()
""",
        default_timeout=30,
    )
    app.session_state["engine"] = engine
    app.session_state["month"] = "All time"
    app.session_state["adherence_plan"] = plan.plan_id
    app.run()
    assert not app.exception and not app.error
    assert len(app.metric) == 3 and len(app.get("plotly_chart")) == 1
    assert app.dataframe[0].value.iloc[0]["Deviation"] == "Below 6–10 reps"
    assert app.dataframe[0].value.iloc[0]["Occurrences / assessed"] == "3/3"
    assert len(app.selectbox) == 1 and not app.caption and not app.button
    app.session_state["month"] = (start.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    app.run()
    assert not app.exception and not app.error and not app.get("plotly_chart")
    assert any("At least three" in item.value for item in app.info)
    assert not any("Deviation" in item.value.columns for item in app.dataframe)
