"""Prepare plan inputs once, then apply decisions for the selected workout."""

from db.exercise_history_load_settings import load_legacy_body_mass_exercise_ids
from db.exercise_starting_history import load_exercise_starting_history
from db.plan_adherence import load_plan_performance
from db.read_cache import read_cached, read_scope
from db.training_plans import load_training_plan_versions
from metrics.history_starting_loads import with_history_starting_loads
from metrics.progression import recommend_workout
from models.plan_context import PlanReadContext, PreparedWorkout
from models.progression import DeloadPolicy, ProgressionPolicy


def prepare_plan_context(engine, plan_id, start, end, *, as_of, versions=None) -> PlanReadContext:
    """Load current plan snapshots, linked history and the requested preview window."""
    if versions is not None and any(version.plan_id != plan_id for version in versions):
        raise ValueError("Plan versions must belong to the selected plan")
    return _current_plan_context(engine, plan_id, start, end, as_of=as_of)


@read_cached
def _current_plan_context(engine, plan_id, start, end, *, as_of):
    versions = tuple(load_training_plan_versions(engine, plan_id))
    history = load_plan_performance(engine, plan_id, start, end)
    return PlanReadContext(plan_id, as_of, versions, history, (start, end))


@read_scope()
def recommend_prepared_workout(
    engine,
    prepared: PreparedWorkout,
    *,
    policy=ProgressionPolicy(),
    deload_policy=DeloadPolicy(),
    substitutions=None,
    replacement_weight_steps=None,
):
    """Use the prepared occurrence as a selection, then read its current inputs."""
    selected = prepared.upcoming.slot
    context = _current_plan_context(
        engine, prepared.plan_id, *prepared.window, as_of=prepared.as_of
    )
    try:
        current = context.prepare_workout(selected.day_id, selected.scheduled_date)
        previous_version = next(v for v in prepared.versions if v.version_id == selected.version_id)
        current_version = next(
            v for v in current.versions if v.version_id == current.upcoming.slot.version_id
        )
        if previous_version.created_at != current_version.created_at:
            raise ValueError("The selected plan version has changed")
    except (ValueError, StopIteration) as exc:
        raise ValueError("The selected workout changed. Prepare the workout again.") from exc
    return _recommend_snapshot(
        engine,
        current,
        policy=policy,
        deload_policy=deload_policy,
        substitutions=substitutions,
        replacement_weight_steps=replacement_weight_steps,
    )


def _recommend_snapshot(
    engine, prepared, *, policy, deload_policy, substitutions, replacement_weight_steps
):
    data, upcoming, as_of = prepared.history, prepared.upcoming, prepared.as_of
    settings = prepared.settings_by_version
    exercise_ids = {
        (substitutions or {}).get(target.plan_exercise_id, target.exercise.exercise_id)
        for target in upcoming.targets
    }
    history = load_exercise_starting_history(
        engine, exercise_ids, as_of=as_of, plan_id=prepared.plan_id
    )
    result = recommend_workout(
        data,
        upcoming,
        as_of=as_of,
        settings=settings[upcoming.slot.version_id],
        settings_by_version=settings,
        policy=policy,
        deload_policy=deload_policy,
        substitutions=substitutions,
        replacement_weight_steps=replacement_weight_steps,
        exercise_history=history,
    )
    if result.block.phase not in ("normal", "unconfigured"):
        return result
    return with_history_starting_loads(
        result,
        upcoming,
        history,
        as_of=as_of,
        manual_load_exercise_ids=data.manual_load_exercise_ids,
        legacy_body_mass_exercise_ids=load_legacy_body_mass_exercise_ids(engine),
        max_history_gap_days=policy.max_history_gap_days,
    )


@read_scope()
@read_cached
def load_workout_recommendations(
    engine,
    plan_id,
    day_id,
    scheduled_date,
    *,
    as_of,
    policy=ProgressionPolicy(),
    deload_policy=DeloadPolicy(),
    substitutions=None,
    replacement_weight_steps=None,
):
    context = prepare_plan_context(engine, plan_id, scheduled_date, scheduled_date, as_of=as_of)
    return _recommend_snapshot(
        engine,
        context.prepare_workout(day_id, scheduled_date),
        policy=policy,
        deload_policy=deload_policy,
        substitutions=substitutions,
        replacement_weight_steps=replacement_weight_steps,
    )


def load_normal_workout_recommendations(
    engine,
    plan_id,
    day_id,
    scheduled_date,
    *,
    as_of,
    policy=ProgressionPolicy(),
    substitutions=None,
    replacement_weight_steps=None,
):
    """Compatibility entry point; reject deload dates rather than prescribe increases."""
    result = load_workout_recommendations(
        engine,
        plan_id,
        day_id,
        scheduled_date,
        as_of=as_of,
        policy=policy,
        substitutions=substitutions,
        replacement_weight_steps=replacement_weight_steps,
    )
    if result.block.phase == "deload":
        raise ValueError("Use load_workout_recommendations for deload dates")
    return result.exercises
