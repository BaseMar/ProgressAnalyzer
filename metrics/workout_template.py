"""Editable phone notes: proposed targets are separate from performed results."""
from metrics.utils.recommendation_text import goal_summary


def workout_template(upcoming, recommendation, exercise_names):
    lines = [f'Date: {upcoming.slot.scheduled_date:%Y-%m-%d}',
             f'Workout: {upcoming.slot.name}', 'Time: __:__ - __:__', '',
             'After training, enter your actual results, load and RIR. Targets are suggestions.', '']
    targets = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    for index, item in enumerate(recommendation.exercises, 1):
        planned = targets[item.plan_exercise_id]
        name = ' '.join(exercise_names.get(item.actual_exercise_id, f'Exercise #{item.actual_exercise_id}').split())
        lines.append(f'{index}. {name}')
        if item.goals:
            prefix = 'Starting loads; ' if item.reason_code == 'reuse_exercise_baseline' else ''
            lines.append('Target: ' + prefix + goal_summary(item))
            results = ['__s' + (f' @ {goal.weight:g} kg' if goal.weight else '') if goal.unit == 'seconds'
                       else (f'__x{goal.weight:g}' if goal.weight is not None else '__x__') for goal in item.goals]
        else:
            unit = 's' if planned.target_unit == 'seconds' else 'reps'
            reserve = str(item.target_rir) if item.target_rir is not None else 'unknown'
            lines.append(f'Target: {planned.set_count} sets, {planned.target_min}–{planned.target_max} {unit}; '
                         f'RIR: {reserve}; load to be selected')
            results = ['__s @ __ kg' if planned.target_unit == 'seconds' else '__x__'] * planned.set_count
        lines.append('Result: ' + ' / '.join(results))
        lines.append('RIR: ' + ' / '.join(['__'] * len(results)))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
