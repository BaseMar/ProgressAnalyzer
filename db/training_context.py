"""Read planned deload context without persisting inferred set labels."""
from datetime import date, datetime

from sqlalchemy import text

from metrics.training_block import is_deload_workout
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import ProgressionSettings
from db.read_cache import read_cached, table_names


@read_cached
def load_deload_exercise_ids(engine, *, as_of=None):
    as_of = as_of or date.today()
    with engine.connect() as connection:
        names = table_names(connection)
        required = {"training_plan_session_links", "training_plan_progression", "training_plan_days"}
        if not required.issubset(names):
            return frozenset()
        rows = connection.execute(text('''
            SELECT l.day_id, d.version_id, d.name, l.scheduled_date, l.session_id,
                   s.session_date, p.block_start, p.block_weeks, we.workout_exercise_id
            FROM training_plan_session_links l
            JOIN training_plan_days d ON d.day_id=l.day_id
            JOIN training_plan_progression p ON p.version_id=d.version_id
            JOIN workout_sessions s ON s.session_id=l.session_id
            JOIN workout_exercises we ON we.session_id=l.session_id
        ''')).mappings().all()
    output = set()
    for row in rows:
        performed = row["session_date"]
        if isinstance(performed, datetime):
            performed = performed.date()
        elif isinstance(performed, str):
            performed = date.fromisoformat(performed[:10])
        scheduled, start = row["scheduled_date"], row["block_start"]
        if isinstance(scheduled, str):
            scheduled = date.fromisoformat(scheduled)
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if performed is None or performed > as_of:
            continue
        slot = ScheduledWorkout(row["day_id"], row["version_id"], scheduled, row["name"], row["session_id"], performed)
        if is_deload_workout(slot, ProgressionSettings(start, row["block_weeks"]), as_of=as_of):
            output.add(row["workout_exercise_id"])
    return frozenset(output)
