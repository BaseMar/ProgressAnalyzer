"""Read-only entry point for normal-session recommendations (before deload integration)."""
from db.plan_adherence import load_plan_performance
from db.training_plans import load_training_plan_version
from metrics.progression import recommend_normal_workout
from models.progression import ProgressionPolicy


def load_normal_workout_recommendations(engine, plan_id, day_id, scheduled_date, *, as_of,
                                        policy=ProgressionPolicy(), substitutions=None, replacement_weight_steps=None):
    data = load_plan_performance(engine, plan_id, scheduled_date, scheduled_date)
    upcoming = next((item for item in data.workouts if item.slot.day_id == day_id
                     and item.slot.scheduled_date == scheduled_date), None)
    if upcoming is None:
        raise ValueError("This workout is not scheduled for the selected plan and date")
    version = load_training_plan_version(engine, upcoming.slot.version_id)
    settings = version.draft.progression
    return recommend_normal_workout(data, upcoming, as_of=as_of,
        block_start=settings.block_start if settings else None, policy=policy,
        substitutions=substitutions, replacement_weight_steps=replacement_weight_steps)
