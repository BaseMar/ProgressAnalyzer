"""Read-only recommendation services using immutable plan-version settings."""
from db.plan_adherence import load_plan_performance
from db.exercise_starting_history import load_exercise_starting_history
from db.exercise_history_load_settings import load_legacy_body_mass_exercise_ids
from db.training_plans import load_training_plan_versions
from metrics.history_starting_loads import HISTORY_START_REASONS, with_history_starting_loads
from metrics.progression import recommend_workout
from models.progression import DeloadPolicy, ProgressionPolicy


def load_normal_workout_recommendations(engine, plan_id, day_id, scheduled_date, *, as_of,
                                        policy=ProgressionPolicy(), substitutions=None, replacement_weight_steps=None):
    """Compatibility entry point; reject deload dates rather than prescribe increases."""
    result = load_workout_recommendations(engine, plan_id, day_id, scheduled_date, as_of=as_of,
        policy=policy, substitutions=substitutions, replacement_weight_steps=replacement_weight_steps)
    if result.block.phase == "deload":
        raise ValueError("Use load_workout_recommendations for deload dates")
    return result.exercises


def load_workout_recommendations(engine, plan_id, day_id, scheduled_date, *, as_of,
                                policy=ProgressionPolicy(), deload_policy=DeloadPolicy(),
                                substitutions=None, replacement_weight_steps=None):
    data = load_plan_performance(engine, plan_id, scheduled_date, scheduled_date)
    upcoming = next((item for item in data.workouts if item.slot.day_id == day_id
                     and item.slot.scheduled_date == scheduled_date), None)
    if upcoming is None:
        raise ValueError("This workout is not scheduled for the selected plan and date")
    settings = {version.version_id: version.draft.progression
                for version in load_training_plan_versions(engine, plan_id)}
    result = recommend_workout(data, upcoming, as_of=as_of, settings=settings[upcoming.slot.version_id],
        settings_by_version=settings, policy=policy, deload_policy=deload_policy,
        substitutions=substitutions, replacement_weight_steps=replacement_weight_steps)
    if result.block.phase not in ('normal', 'unconfigured'):
        return result
    exercise_ids = {item.actual_exercise_id for item in result.exercises
        if item.reason_code in HISTORY_START_REASONS or any(g.load_type == 'manual_bodyweight' for g in item.goals)}
    history = load_exercise_starting_history(engine, exercise_ids, as_of=as_of)
    return with_history_starting_loads(result, upcoming, history, as_of=as_of,
        manual_load_exercise_ids=data.manual_load_exercise_ids,
        legacy_body_mass_exercise_ids=load_legacy_body_mass_exercise_ids(engine),
        max_history_gap_days=policy.max_history_gap_days)
