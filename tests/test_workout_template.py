"""Copied notes keep targets separate from the user's performed workout."""
from datetime import date
from types import SimpleNamespace

import pytest

from metrics.workout_template import workout_template
from models.plan_adherence import PlannedTarget, PlannedWorkout
from models.progression import ExerciseRecommendation, SetGoal, TrainingBlockPhase, WorkoutRecommendation
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise
from ui.sidebar_upload import SidebarUpload
from test_next_workout_view import seed, start_app
from test_plan_schedule import schedule_data


def note(goals=(), *, unit='reps', reason='reuse_exercise_baseline', actual_id=2, rir=2):
    plan = PlannedExercise(1, 3, 30 if unit == 'seconds' else 6, 60 if unit == 'seconds' else 10, unit)
    upcoming = PlannedWorkout(ScheduledWorkout(10, 1, date(2026, 11, 9), 'Upper A'), (PlannedTarget(1, plan),))
    recommendation = ExerciseRecommendation(1, 1, actual_id, upcoming.slot.scheduled_date,
        'maintain' if goals else 'insufficient_data', tuple(goals), rir, reason, '')
    return workout_template(upcoming, WorkoutRecommendation(TrainingBlockPhase('normal'), (recommendation,)),
                            {1: 'Bench Press', 2: 'Machine Chest Press'})


@pytest.fixture
def parser(monkeypatch):
    monkeypatch.setattr('ui.sidebar_upload.st.sidebar', SimpleNamespace(warning=lambda _: None))
    return object.__new__(SidebarUpload)


def test_untouched_template_cannot_import_suggested_results(parser):
    text = note([SetGoal(80., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps')])
    assert 'Date: 2026-11-09' in text
    assert '1. Machine Chest Press' in text
    assert 'Starting loads' in text
    assert 'Result: __x80 / __x70 / __x70' in text
    assert 'RIR: __ / __ / __' in text
    assert parser._parse_txt(text) is None


@pytest.mark.parametrize('target_label,result_label', [('Target:', 'Result:'), ('Cel:', 'Wynik:')])
def test_completed_template_imports_actual_values_and_preserves_unknown_rir_positions(parser, target_label, result_label):
    text = note([SetGoal(80., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps')])
    text = text.replace('Result: __x80 / __x70 / __x70', 'Result: 8x75 / 11x65 / 10x65')
    text = text.replace('RIR: __ / __ / __', 'RIR: __ / 2 / 0')
    text = text.replace('Target:', target_label).replace('Result:', result_label)
    assert parser._parse_txt(text) == [{'name': 'Machine Chest Press', 'sets': [
        {'reps': 8, 'weight': 75., 'rir': None},
        {'reps': 11, 'weight': 65., 'rir': 2},
        {'reps': 10, 'weight': 65., 'rir': 0},
    ]}]


@pytest.mark.parametrize('result', ['__x80 / 11x65 / __x70', '8x__ / 11x65 / __x70'])
@pytest.mark.parametrize('result_label', ['Result:', 'Wynik:'])
def test_partial_note_keeps_rir_assigned_to_its_actual_set(parser, result, result_label):
    text = note([SetGoal(80., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps'), SetGoal(70., 10, 12, 'reps')])
    text = text.replace('Result: __x80 / __x70 / __x70', 'Result: ' + result)
    text = text.replace('RIR: __ / __ / __', 'RIR: __ / 2 / 0')
    text = text.replace('Result:', result_label)
    assert parser._parse_txt(text)[0]['sets'] == [{'reps': 11, 'weight': 65., 'rir': 2}]


def test_missing_recommendation_keeps_exercise_and_unknown_weight(parser):
    text = note(reason='no_history', actual_id=1)
    assert '1. Bench Press' in text
    assert 'load to be selected' in text
    assert 'Result: __x__ / __x__ / __x__' in text
    assert parser._parse_txt(text) is None


def test_deload_template_uses_reduced_goal_count_and_target_reserve(parser):
    text = note([SetGoal(52.5, 6, 6, 'reps')] * 2, reason='scheduled_deload', rir=4)
    assert '2 × 6 reps' in text and 'RIR ≥ 4' in text
    assert 'Result: __x52.5 / __x52.5' in text
    assert '\nRIR: __ / __\n' in text
    assert parser._parse_txt(text) is None


def test_timed_template_keeps_duration_and_recorded_load_on_import(parser):
    text = note([SetGoal(5., 30, 60, 'seconds')] * 3, unit='seconds', rir=None)
    assert 'Result: __s @ 5 kg / __s @ 5 kg / __s @ 5 kg' in text
    assert parser._parse_txt(text) is None
    text = text.replace('Result: __s @ 5 kg / __s @ 5 kg / __s @ 5 kg',
                        'Result: 45s @ 5 kg / 40s @ 5 kg / 35s @ 5 kg')
    assert parser._parse_txt(text)[0]['sets'] == [
        {'reps': duration, 'weight': 5., 'rir': None, 'duration_seconds': duration}
        for duration in (45, 40, 35)
    ]


@pytest.mark.parametrize('label', ['Cel', 'Target', 'Plan'])
def test_import_ignores_target_lines_and_retains_measured_rir(parser, label):
    parsed = parser._parse_txt(f'1. Row\n{label}: 3 x 10 reps; RIR 3\n8x60 / 8x60\nRIR: ? / 1\n')
    assert parsed[0]['sets'] == [{'reps': 8, 'weight': 60., 'rir': None}, {'reps': 8, 'weight': 60., 'rir': 1}]


def test_copy_preview_tracks_selected_alternative_and_weight_step(schedule_data):
    engine, _, _, _ = schedule_data
    plan = seed(schedule_data, actual_id=2)
    app = start_app(engine, plan)
    assert len(app.code) == 1
    assert '1. Barbell Bench Press' in app.code[0].value
    assert 'Result: __x__ / __x__ / __x__' in app.code[0].value
    next(item for item in app.selectbox if item.key.endswith('_exercise')).select(2).run()
    next(item for item in app.number_input if 'Weight step' in item.label).set_value(5.).run()
    assert not app.exception
    assert '1. Machine Chest Press' in app.code[0].value
    assert 'Result: __x65 / __x65 / __x65' in app.code[0].value
    assert '1. Barbell Bench Press' not in app.code[0].value
