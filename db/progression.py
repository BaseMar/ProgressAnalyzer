"""Read-only recommendation services using immutable plan-version settings."""
from db.plan_adherence import load_plan_performance
from db.training_plans import load_training_plan_versions
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
    return recommend_workout(data, upcoming, as_of=as_of, settings=settings[upcoming.slot.version_id],
        settings_by_version=settings, policy=policy, deload_policy=deload_policy,
        substitutions=substitutions, replacement_weight_steps=replacement_weight_steps)
