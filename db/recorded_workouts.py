"""Read recorded exercises and set snapshots independently of plan matching."""

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, literal, select

from db.read_cache import has_table, read_cached
from db.set_classifications import classifications
from db.set_loads import loads
from mapper import map_recorded_exercises

metadata = MetaData()
actual_exercises = Table(
    "workout_exercises",
    metadata,
    Column("workout_exercise_id", Integer, primary_key=True),
    Column("session_id", Integer),
    Column("exercise_id", Integer),
)
actual_sets = Table(
    "workout_sets",
    metadata,
    Column("set_id", Integer, primary_key=True),
    Column("workout_exercise_id", Integer),
    Column("set_number", Integer),
    Column("repetitions", Integer),
    Column("weight", Float),
    Column("rir", Integer),
    Column("duration_seconds", Integer),
)
catalog_exercises = Table(
    "exercises",
    metadata,
    Column("exercise_id", Integer, primary_key=True),
    Column("exercise_name", String),
)


@read_cached
def load_recorded_exercises(connection, session_ids, *, exercise_ids=None):
    """Read full selected sessions, optionally restricted to exact exercise IDs.

    Selection policies (linked progression, usable starting history and latest
    raw references) belong to callers; this reader does not infer plan matches.
    """
    if not session_ids:
        return ()
    exercise_filter = [actual_exercises.c.session_id.in_(session_ids)]
    if exercise_ids is not None:
        exercise_filter.append(actual_exercises.c.exercise_id.in_(exercise_ids))
    exercises = (
        connection.execute(select(actual_exercises).where(*exercise_filter)).mappings().all()
    )
    load_fields = ("load_type", "body_mass_kg", "assistance_kg")
    load_storage = has_table(connection, loads.name)
    columns = [loads.c[name] if load_storage else literal(None).label(name) for name in load_fields]
    query = (
        select(actual_sets, classifications.c.is_warmup, *columns)
        .outerjoin(
            classifications,
            classifications.c.set_id == actual_sets.c.set_id,
        )
        .join(
            actual_exercises,
            actual_sets.c.workout_exercise_id == actual_exercises.c.workout_exercise_id,
        )
    )
    if load_storage:
        query = query.outerjoin(loads, loads.c.set_id == actual_sets.c.set_id)
    rows = (
        connection.execute(query.where(*exercise_filter).order_by(actual_sets.c.set_number))
        .mappings()
        .all()
    )
    return map_recorded_exercises(exercises, rows)
