"""Choose recorded evidence separately from strict progression comparisons."""
from collections import Counter
from dataclasses import replace
from datetime import date

from metrics.plan_performance import compute_plan_performance
from models.plan_adherence import PlannedTarget


def with_recorded_baselines(data, performances, planned, actual_id, *, as_of):
    """Include exact-ID records absent from an old workout's prescription.

    A session link establishes its date, workout and block even when a recorded
    exercise wasn't in that version of the routine. Project that observation
    onto the upcoming prescription using the ordinary set interpretation rules.
    Such rows supply starting loads only; they never establish plan coverage,
    replacements or upper-range confirmations for the historical workout.
    """
    represented = {(row['session_id'], row['actual_exercise_id']) for row in performances}
    occurrences = Counter((item.session_id, item.exercise_id) for item in data.recorded)
    workouts = {item.slot.session_id: item for item in data.workouts if item.slot.session_id is not None}
    extra = []
    for recorded in data.recorded:
        key = recorded.session_id, recorded.exercise_id
        if recorded.exercise_id != actual_id or key in represented or occurrences[key] != 1:
            continue
        workout = workouts.get(recorded.session_id)
        if workout is None:
            continue
        projected = replace(workout, targets=(PlannedTarget(-recorded.workout_exercise_id,
                            replace(planned, exercise_id=actual_id)),))
        observation = replace(data, workouts=(projected,), recorded=(recorded,), matches=())
        for row in compute_plan_performance(observation, as_of=as_of):
            extra.append({**row, 'baseline_only': True})
    if not extra:
        return performances
    order = {sid: index for index, sid in enumerate(data.session_order)}
    return sorted([*performances, *extra], key=lambda row: (
        row['performed_on'] or date.max, order.get(row['session_id'], row['session_id'] or 0), row['day_id']))


def workout_exercise_identity(context):
    """An exercise's workout identity survives target and order revisions."""
    return context[0], context[1], context[2], context[4], context[6]


def recommendation_history(performances, context, *, as_of, block_start):
    """Return strict history or a baseline of the exact same actual exercise.

    The latest execution in this workout takes priority, including incomplete
    or empty records. Another workout is only a baseline when this workout has
    no execution of the selected actual exercise. Different catalog IDs never
    share loads, and a changed prescription never inherits confirmations.
    """
    actual_id, unit = context[5], context[6]
    candidates = [row for row in performances
                  if row['actual_exercise_id'] == actual_id and row['unit'] == unit
                  and row['session_id'] is not None and row['performed_on'] is not None
                  and row['performed_on'] <= as_of
                  and (block_start is None or row['performed_on'] >= block_start)]
    local = [row for row in candidates
             if workout_exercise_identity(row['context']) == workout_exercise_identity(context)]
    if local:
        occurrences = Counter((row['session_id'], row['day_id']) for row in local)
        if any(count > 1 for count in occurrences.values()):
            # Repeated positions of the same exercise have no unambiguous
            # transferable identity after order/target changes.
            return [row for row in local if row['context'] == context and not row.get('baseline_only')], False
        latest = local[-1]
        if latest.get('baseline_only'):
            return [latest], True
        if latest['context'] == context:
            # Do not bridge an intervening prescription/order change on return.
            history = []
            for row in reversed(local):
                if row['context'] != context or row.get('baseline_only'):
                    break
                history.append(row)
            return list(reversed(history)), False
        return [latest], True
    return (candidates[-1:], True) if candidates else ([], False)
