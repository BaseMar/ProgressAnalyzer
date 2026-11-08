"""Auditable observations, evidence barriers and reuse of actual targets."""
from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from test_plan_performance import data, execution
from metrics.progression import recommend_workout
from metrics.training_insights import compute_training_insights
from models.plan_adherence import PlannedTarget, PlannedWorkout
from models.scheduled_workout import ScheduledWorkout
from models.training_insights import InsightPolicy, WorkoutPreview
from models.training_plan import PlannedExercise, ProgressionSettings

FIRST, SECOND, THIRD = date(2026, 5, 4), date(2026, 5, 11), date(2026, 5, 18)
AS_OF, NEXT = date(2026, 5, 20), date(2026, 5, 25)
PLAN = PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5)
SETTINGS = ProgressionSettings(FIRST, 7)


def report(*entries, **kwargs):
    return compute_training_insights(data(*entries), as_of=AS_OF, **kwargs)


def only(*entries, **kwargs):
    result = report(*entries, **kwargs)
    assert len(result.annotations) == 1
    return result.annotations[0]


def mixed_rir(entry, values):
    workout, recorded, match = entry
    return workout, replace(recorded, sets=tuple(replace(item, rir=rir) for item, rir in zip(recorded.sets, values))), match


def test_more_reps_are_reproducible_from_immutable_sources():
    insight = only(execution(1, FIRST), execution(2, SECOND, (10, 10, 9)))
    assert insight.code == "more_output"
    assert insight.observation == "2 more reps at the same load and RIR"
    old, new = insight.sources
    assert (old.session_id, new.session_id) == (1, 2)
    assert sum(item.quantity for item in new.sets) - sum(item.quantity for item in old.sets) == 2
    assert all(item.source == "rir" and item.kind == "working" for item in new.sets)
    with pytest.raises(FrozenInstanceError):
        new.sets[0].rir = 0


@pytest.mark.parametrize("values, weight, expected", [
    ((8, 8, 7), 65, "load_changed"),
    ((8, 8, 7), 60, "less_output"),
    ((10, 9, 8), 60, "same_output"),
])
def test_load_and_output_are_separate_observations(values, weight, expected):
    insight = only(execution(1, FIRST), execution(2, SECOND, values, weight=weight))
    assert insight.code == expected
    assert "regression" not in insight.observation.lower()
    assert "fatigue" not in insight.observation.lower()
    assert "60 kg" in insight.evidence
    if weight != 60:
        assert "65 kg" in insight.evidence


def test_equal_average_rir_does_not_hide_effort_changes_per_set():
    planned = replace(PLAN, target_rir=None)
    insight = only(mixed_rir(execution(1, FIRST, planned=planned), (1, 2, 3)),
                   mixed_rir(execution(2, SECOND, (10, 10, 9), planned=planned), (3, 2, 1)))
    assert insight.code == "effort_changed"
    assert "RIR 1/2/3" in insight.evidence and "RIR 3/2/1" in insight.evidence


def test_more_output_with_less_reserve_is_not_labelled_progress():
    insight = only(execution(1, FIRST, rir=3), execution(2, SECOND, (10, 10, 9), rir=2))
    assert insight.code == "effort_changed"


def test_less_than_target_rir_is_actionable_even_for_first_execution():
    insight = only(mixed_rir(execution(1, FIRST), (2, 1, 2)))
    assert insight.code == "below_target_rir"
    assert insight.evidence_level == "observed"
    assert "planned RIR ≥ 2" in insight.evidence


@pytest.mark.parametrize("options, reason", [
    ({"rir": None}, "missing RIR"),
    ({"values": (10, 9)}, "incomplete set count"),
    ({"values": ()}, "no matching working sets"),
    ({"rir": 4}, "only light/low-effort work"),
    ({"rir": 6}, "only light/low-effort work"),
])
def test_latest_incomplete_execution_never_falls_back_to_older_success(options, reason):
    latest = execution(3, THIRD, **options)
    insight = only(execution(1, FIRST), execution(2, SECOND, (10, 10, 9)), latest)
    assert insight.code == "limited_evidence"
    assert reason in insight.evidence
    assert insight.sources[-1].session_id == 3


def test_incomplete_previous_execution_is_a_barrier_too():
    insight = only(execution(1, FIRST), execution(2, SECOND, (10, 9)), execution(3, THIRD))
    assert insight.code == "limited_evidence"
    assert "previous execution: incomplete" in insight.evidence
    assert [item.session_id for item in insight.sources] == [2, 3]


def test_first_baselines_are_grouped_and_alternatives_keep_their_own_evidence():
    result = report(execution(1, FIRST), execution(2, SECOND, actual_id=2),
                    execution(3, THIRD, (10, 10, 9), actual_id=2))
    paired = next(item for item in result.annotations if item.code == "more_output")
    assert paired.exercise_id == 2
    assert [source.session_id for source in paired.sources] == [2, 3]
    limited = next(item for item in result.annotations if item.code == "limited_evidence")
    assert "1 × first comparable execution" in limited.evidence


def test_target_change_and_manual_block_reset_do_not_compare_across_contexts():
    second = execution(2, SECOND)
    second = (replace(second[0], slot=replace(second[0].slot, version_id=2)), second[1], None)
    result = report(execution(1, FIRST), second,
                    settings_by_version={1: SETTINGS, 2: ProgressionSettings(SECOND, 6)})
    assert result.assessed_contexts == 0
    assert result.limited_contexts == 2
    assert "2 × first comparable execution" in result.annotations[0].evidence
    result = report(execution(1, FIRST), execution(2, SECOND, planned=replace(PLAN, target_min=8)))
    assert result.assessed_contexts == 0


def test_history_across_month_filter_and_actual_chronology():
    april = execution(1, date(2026, 4, 27))
    insight = only(april, execution(2, FIRST, (10, 10, 9)), start=FIRST, end=date(2026, 5, 31))
    assert insight.code == "more_output"
    assert insight.sources[0].performed_on == date(2026, 4, 27)
    first = execution(1, FIRST, (10, 10, 9))
    second = execution(2, SECOND)
    first = (replace(first[0], slot=replace(first[0].slot, performed_on=THIRD)), first[1], None)
    insight = only(first, second)
    assert [item.session_id for item in insight.sources] == [2, 1]


def test_future_actual_logs_never_generate_an_observation():
    future = execution(2, SECOND, (10, 10, 9))
    future = (replace(future[0], slot=replace(future[0].slot, performed_on=NEXT)), future[1], None)
    result = report(execution(1, FIRST), future)
    assert result.assessed_contexts == 0
    assert not any(item.code == "more_output" for item in result.annotations)


def test_same_day_and_long_gap_are_limited_not_progress():
    first = execution(1, FIRST)
    same_day = execution(2, SECOND)
    same_day = (replace(same_day[0], slot=replace(same_day[0].slot, performed_on=FIRST)), same_day[1], None)
    assert "same day" in only(first, same_day).evidence
    result = compute_training_insights(data(first, execution(2, date(2026, 6, 1))), as_of=date(2026, 6, 2))
    assert "gap over 21 days" in result.annotations[0].evidence


def test_unlinked_elapsed_dates_are_one_linkage_note_not_skipped_workouts():
    workouts = tuple(replace(execution(sid, day)[0], slot=ScheduledWorkout(10, 1, day, "Upper A"))
                     for sid, day in enumerate((FIRST, SECOND, AS_OF, NEXT), 1))
    result = compute_training_insights(replace(data(), workouts=workouts), as_of=AS_OF)
    insight = result.annotations[0]
    assert len(result.annotations) == 1
    assert "2 elapsed planned workouts without linked logs" in insight.evidence
    assert all(source.session_id is None for source in insight.sources)
    assert "skipped" not in insight.observation + insight.evidence + insight.action


def test_timed_work_needs_no_rir_and_does_not_propose_automatic_timed_increases():
    planned = PlannedExercise(1, 2, 30, 60, "seconds")
    insight = only(execution(1, FIRST, (30, 30), weight=0, rir=None, planned=planned),
                   execution(2, SECOND, (35, 40), weight=0, rir=None, planned=planned))
    assert insight.code == "more_output"
    assert insight.observation == "15 more seconds at the same load"
    assert insight.next_target is None


def test_deload_is_grouped_and_never_labelled_lower_output():
    lighter = execution(2, date(2026, 6, 15), (6, 6), weight=52.5, rir=4, planned=PLAN)
    result = compute_training_insights(data(execution(1, date(2026, 6, 8), planned=PLAN), lighter),
        as_of=date(2026, 6, 16), settings_by_version={1: SETTINGS})
    assert [item.code for item in result.annotations] == ["deload"]
    assert result.annotations[0].sources[0].planned_sets == 3
    assert result.annotations[0].sources[0].phase == "deload"


def preview_for(history):
    upcoming = PlannedWorkout(ScheduledWorkout(10, 1, NEXT, "Upper A"), (PlannedTarget(101, PLAN),))
    result = recommend_workout(history, upcoming, as_of=AS_OF, settings=SETTINGS, settings_by_version={1: SETTINGS})
    return WorkoutPreview(upcoming, result)


def test_numeric_action_reuses_real_progression_target_and_preserves_audit():
    history = data(execution(1, FIRST, (10, 10, 10), planned=PLAN), execution(2, SECOND, (10, 10, 10), planned=PLAN))
    preview = preview_for(history)
    result = compute_training_insights(history, as_of=AS_OF, settings_by_version={1: SETTINGS}, preview=preview)
    insight = result.annotations[0]
    assert insight.code == "same_output"
    assert "62.5 kg · 3 × 6 reps · RIR ≥ 2" in insight.action
    assert insight.recommendation == preview.recommendation.exercises[0]
    assert insight.recommendation.reason_code == "upper_range_confirmed"


def test_current_numeric_targets_are_not_attached_to_historical_window_or_wrong_exercise():
    history = data(execution(1, FIRST, planned=PLAN), execution(2, SECOND, planned=PLAN))
    preview = preview_for(history)
    historical = compute_training_insights(history, as_of=AS_OF, end=THIRD, settings_by_version={1: SETTINGS}, preview=preview)
    assert historical.annotations[0].next_target is None
    changed = replace(preview, upcoming=replace(preview.upcoming, slot=replace(preview.upcoming.slot, name="Lower A")))
    other = compute_training_insights(history, as_of=AS_OF, settings_by_version={1: SETTINGS}, preview=changed)
    assert other.annotations[0].next_target is None


def test_at_most_three_annotations_prioritize_attention_and_group_data_gaps():
    entries = []
    for index in range(5):
        for sid, day, values in ((index * 2 + 1, FIRST, (10, 9, 8)), (index * 2 + 2, SECOND, (10, 10, 9))):
            item = execution(sid, day, values, rir=1 if index == 4 else 2)
            entries.append((replace(item[0], slot=replace(item[0].slot, day_id=index + 10, name=f"Workout {index}")), item[1], None))
    result = report(*entries)
    assert len(result.annotations) == 3
    assert result.annotations[0].code == "below_target_rir"
    assert result.omitted_annotations == 2
    assert report(*entries, policy=InsightPolicy(max_annotations=1)).omitted_annotations == 4


def test_ui_shows_action_and_source_disclosure_and_escapes_catalog_names():
    result = report(execution(1, FIRST), execution(2, SECOND, (10, 10, 9)))
    app = AppTest.from_string('''
import streamlit as st
from ui.training_insights_view import render_training_insights
render_training_insights(st.session_state['report'], {1: '<script>alert(1)</script>'})
''')
    app.session_state['report'] = result
    app.run()
    assert not app.exception
    html = next(item.value for item in app.markdown if 'analysis-insight' in item.value)
    assert '&lt;script&gt;' in html and '<script>' not in html
    assert '2 more reps' in html and 'Next workout target' in html
    assert len(app.expander) == 1
    assert app.expander[0].label.startswith('Why?')
    assert len(app.json) == 1
