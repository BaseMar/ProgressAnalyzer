"""Calendar-based, repeating blocks and temporary deload targets."""
from dataclasses import replace
from datetime import date, timedelta
from math import ceil

from models.progression import DeloadPolicy, TrainingBlockPhase
from models.training_plan import ProgressionSettings


def training_block_phase(on_date: date, settings: ProgressionSettings | None) -> TrainingBlockPhase:
    """Weeks are seven-day intervals from the saved anchor, not calendar weeks."""
    if type(on_date) is not date:
        raise ValueError("Training date must be a date")
    if settings is None:
        return TrainingBlockPhase("unconfigured")
    elapsed = (on_date - settings.block_start).days
    if elapsed < 0:
        return TrainingBlockPhase("not_started")
    length = settings.block_weeks * 7
    cycle, offset = divmod(elapsed, length)
    start = settings.block_start + timedelta(days=cycle * length)
    deload = start + timedelta(days=length - 7)
    return TrainingBlockPhase("deload" if offset >= length - 7 else "normal",
                              cycle + 1, offset // 7 + 1, start,
                              start + timedelta(days=length - 1), deload)


def is_deload_workout(slot, settings, *, as_of=None):
    """A moved deload stays deload; ordinary work done during deload is excluded too."""
    return (training_block_phase(slot.scheduled_date, settings).phase == "deload"
            or (slot.performed_on is not None
                and (as_of is None or slot.performed_on <= as_of)
                and training_block_phase(slot.performed_on, settings).phase == "deload"))


def deload_exercise_target(planned, policy=DeloadPolicy()):
    """Derived expectations only; the saved plan is never changed."""
    count = max(1, ceil(planned.set_count * policy.retained_set_fraction))
    if planned.target_unit == "seconds":
        # No automatic timed/load prescription in this stage: leave targets intact.
        return planned
    rir = max(policy.minimum_rir, planned.target_rir + policy.extra_rir) if planned.target_rir is not None else None
    return replace(planned, set_count=count, target_max=planned.target_min, target_rir=rir)


def deload_adjusted_input(data, settings_by_version, policy=DeloadPolicy(), *, as_of=None):
    """Use reduced counts/ranges in plan coverage, without writing new snapshots."""
    return replace(data, workouts=tuple(
        replace(workout, targets=tuple(replace(target, exercise=deload_exercise_target(target.exercise, policy))
                                       for target in workout.targets))
        if is_deload_workout(workout.slot, settings_by_version.get(workout.slot.version_id), as_of=as_of) else workout
        for workout in data.workouts))
