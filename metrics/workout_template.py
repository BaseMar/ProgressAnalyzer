"""Editable phone notes: proposed targets are separate from performed results."""
from metrics.utils.recommendation_text import goal_summary


def workout_template(upcoming, recommendation, exercise_names):
    lines = [f'Data: {upcoming.slot.scheduled_date:%Y-%m-%d}',
             f'Trening: {upcoming.slot.name}', 'Godzina: __:__ - __:__', '',
             'Po treningu wpisz faktyczny wynik, ciężar i RIR. Cel jest wskazówką.', '']
    targets = {target.plan_exercise_id: target.exercise for target in upcoming.targets}
    for index, item in enumerate(recommendation.exercises, 1):
        planned = targets[item.plan_exercise_id]
        name = ' '.join(exercise_names.get(item.actual_exercise_id, f'Exercise #{item.actual_exercise_id}').split())
        lines.append(f'{index}. {name}')
        if item.goals:
            prefix = 'Ciężary wyjściowe; ' if item.reason_code == 'reuse_exercise_baseline' else ''
            lines.append('Cel: ' + prefix + goal_summary(item))
            results = ['__s' + (f' @ {goal.weight:g} kg' if goal.weight else '') if goal.unit == 'seconds'
                       else f'__x{goal.weight:g}' for goal in item.goals]
        else:
            unit = 's' if planned.target_unit == 'seconds' else 'powt.'
            reserve = str(item.target_rir) if item.target_rir is not None else 'nieustalony'
            lines.append(f'Cel: {planned.set_count} serie, {planned.target_min}–{planned.target_max} {unit}; '
                         f'RIR: {reserve}; ciężar do ustalenia')
            results = ['__s @ __ kg' if planned.target_unit == 'seconds' else '__x__'] * planned.set_count
        lines.append('Wynik: ' + ' / '.join(results))
        lines.append('RIR: ' + ' / '.join(['__'] * len(results)))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
