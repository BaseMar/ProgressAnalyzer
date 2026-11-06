"""Choose recorded evidence separately from strict progression comparisons."""
from collections import Counter


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
            return [row for row in local if row['context'] == context], False
        latest = local[-1]
        if latest['context'] == context:
            # Do not bridge an intervening prescription/order change on return.
            history = []
            for row in reversed(local):
                if row['context'] != context:
                    break
                history.append(row)
            return list(reversed(history)), False
        return [latest], True
    return (candidates[-1:], True) if candidates else ([], False)
