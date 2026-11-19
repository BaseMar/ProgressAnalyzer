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


@read_cached
def prepare_plan_context(engine, plan_id, start, end, *, as_of, versions=None) -> PlanReadContext:
    """Load full linked history and explicit preview dates, not a filtered chart.

    Supplied versions must belong to this plan. They let a caller share its
    already loaded snapshots within the same render; no context is persisted.
    """
    versions = tuple(load_training_plan_versions(engine, plan_id) if versions is None else versions)
    if any(version.plan_id != plan_id for version in versions):
        raise ValueError("Plan versions must belong to the selected plan")
    history = load_plan_performance(engine, plan_id, start, end)
    return PlanReadContext(plan_id, as_of, versions, history)


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
    """Apply one decision engine to linked and unlinked exact-exercise history."""
    data, upcoming, as_of = prepared.history, prepared.upcoming, prepared.as_of
    settings = prepared.settings_by_version
    exercise_ids = {
        (substitutions or {}).get(target.plan_exercise_id, target.exercise.exercise_id)
        for target in upcoming.targets
    }
    history = load_exercise_starting_history(engine, exercise_ids, as_of=as_of)
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
    return recommend_prepared_workout(
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
