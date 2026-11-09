"""Capture semantic outputs from synthetic data for later optimization comparisons."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from math import isfinite
from numbers import Integral, Real
from unittest.mock import patch

from data_loader import load_data
from db.plan_adherence import load_plan_performance
from db.plan_schedule import load_scheduled_workouts
from db.progression import load_workout_recommendations
from db.training_plans import load_training_plan_versions
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.measurement_timeline import measurement_timeline
from metrics.muscle_volume import weekly_plan_allocation
from metrics.plan_adherence import compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.progression import recommend_workout
from models.plan_adherence import PlanAdherenceInput, PlannedTarget, PlannedWorkout, RecordedExercise
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import PlannedExercise, ProgressionSettings
from models.workout_set import WorkoutSet
from scripts.baseline_fixture import AS_OF, FIXTURE_VERSION


def normalized(value):
    if isinstance(value, dict):
        return {str(key): normalized(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [normalized(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((normalized(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, (Real, Decimal)):
        return round(float(value), 8) if isfinite(value) else None
    raise TypeError(f'Unsupported snapshot value: {type(value).__name__}')


def digest(value):
    payload = json.dumps(normalized(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def load_input(engine):
    # Bypass both Streamlit caches for the semantic snapshot. The render benchmark
    # below exercises the real entry point and its existing cache boundaries.
    with patch('data_manager.get_engine', return_value=engine):
        return getattr(load_data, '__wrapped__', load_data)()


def recommendation_values(result):
    return dict(phase=result.block.phase, exercises=[dict(
        exercise=item.actual_exercise_id, planned_exercise=item.planned_exercise_id,
        action=item.action, reason=item.reason_code, rir=item.target_rir, rir_max=item.target_rir_max,
        goals=[[g.weight, g.minimum, g.maximum, g.unit, g.load_type, g.assistance_kg] for g in item.goals],
        source_sessions=item.evidence_session_ids, source_dates=item.evidence_dates,
    ) for item in result.exercises])


def phase_cases():
    planned = PlannedExercise(1, 3, 6, 10, target_rir=2, weight_increment=2.5)
    target = PlannedTarget(1, planned)
    ordinary = PlannedWorkout(ScheduledWorkout(1, 1, AS_OF - timedelta(days=7), 'Ordinary',
        session_id=1, performed_on=AS_OF - timedelta(days=7)), (target,))
    recorded = RecordedExercise(100, 1, 1, tuple(WorkoutSet(100, n, 10, 60., 2, is_warmup=False) for n in (1, 2, 3)))
    upcoming = PlannedWorkout(ScheduledWorkout(1, 1, AS_OF, 'Ordinary'), (target,))
    data = PlanAdherenceInput((ordinary,), (recorded,), ())
    normal = recommend_workout(data, upcoming, as_of=AS_OF, settings=None)
    settings = ProgressionSettings(AS_OF - timedelta(weeks=6), 7)
    deload = recommend_workout(data, upcoming, as_of=AS_OF, settings=settings)
    return_day = AS_OF + timedelta(days=7)
    returning = PlannedWorkout(ScheduledWorkout(1, 1, return_day, 'Ordinary'), (target,))
    returned = recommend_workout(data, returning, as_of=return_day, settings=settings)
    return {name: recommendation_values(result) for name, result in
            (('ordinary_increase', normal), ('deload', deload), ('return_after_deload', returned))}


def capture_snapshot(engine, plan, *, as_of=AS_OF):
    input_data, _ = load_input(engine)
    start = as_of - timedelta(days=27)
    history = load_plan_performance(engine, plan.plan_id, start, as_of)
    versions = load_training_plan_versions(engine, plan.plan_id)
    settings = {version.version_id: version.draft.progression for version in versions}
    slots = [slot for slot in load_scheduled_workouts(engine, plan.plan_id, as_of, as_of + timedelta(days=6))
             if slot.session_id is None]
    recommendations = {slot.name: recommendation_values(load_workout_recommendations(engine, plan.plan_id,
        slot.day_id, slot.scheduled_date, as_of=as_of)) for slot in slots}
    return normalized(dict(
        fixture=dict(version=FIXTURE_VERSION, as_of=as_of, sessions=len(input_data.sessions),
            recorded_exercises=len(input_data.workout_exercises), sets=len(input_data.sets),
            catalog_exercises=len(input_data.exercises)),
        recommendations=recommendations,
        phase_cases=phase_cases(),
        adherence=compute_plan_adherence(history, as_of=as_of, settings_by_version=settings)['summary'],
        plan_performance=compute_plan_performance(history, as_of=as_of, start=start, end=as_of,
            settings_by_version=settings),
        recorded_exercises=compute_exercise_metrics(input_data),
        weekly_allocation=weekly_plan_allocation(plan.draft, input_data),
        measurements=measurement_timeline(input_data),
    ))


def snapshot_reference(snapshot):
    first = snapshot['recommendations']['Upper A']['exercises']
    return dict(fixture=snapshot['fixture'],
        sections={name: digest(value) for name, value in snapshot.items() if name != 'fixture'},
        examples=dict(upper_a=[dict(exercise=item['exercise'], action=item['action'], reason=item['reason'],
            weights=[g[0] for g in item['goals']]) for item in first],
            phases={name: [g[0] for g in result['exercises'][0]['goals']]
                    for name, result in snapshot['phase_cases'].items()}))
