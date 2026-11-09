"""Read exact-exercise history across plans without creating plan assignments."""
from datetime import date, datetime, timedelta

from sqlalchemy import select

from db.plan_adherence import _recorded, actual_exercises
from db.plan_schedule import links, sessions
from db.training_context import load_deload_exercise_ids
from db.training_plans import days
from db.read_cache import read_cached


@read_cached
def load_exercise_starting_history(engine, exercise_ids, *, as_of):
    if type(as_of) is not date:
        raise ValueError('History cutoff must be a date')
    if not exercise_ids:
        return {}
    query = select(actual_exercises, sessions.c.session_date, days.c.name.label('workout')).join(
        sessions, sessions.c.session_id == actual_exercises.c.session_id
    ).outerjoin(links, links.c.session_id == sessions.c.session_id).outerjoin(
        days, days.c.day_id == links.c.day_id
    ).where(actual_exercises.c.exercise_id.in_(exercise_ids),
            sessions.c.session_date < as_of + timedelta(days=1)).order_by(
        sessions.c.session_date.desc(), sessions.c.start_time.desc().nullslast(),
        sessions.c.session_id.desc(), actual_exercises.c.workout_exercise_id)
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
        recorded = {item.workout_exercise_id: item for item in _recorded(connection,
            {row['session_id'] for row in rows}, exercise_ids=exercise_ids)}
    deload_ids = load_deload_exercise_ids(engine, as_of=as_of)
    result = {}
    for row in rows:
        if row['workout_exercise_id'] in deload_ids:
            continue
        performed = row['session_date']
        if isinstance(performed, datetime):
            performed = performed.date()
        result.setdefault(row['exercise_id'], []).append({
            'session_id': row['session_id'], 'date': performed, 'workout': row['workout'],
            'workout_exercise_id': row['workout_exercise_id'],
            'sets': recorded[row['workout_exercise_id']].sets,
        })
    return result
