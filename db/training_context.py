"""Read planned deload context without persisting inferred set labels."""

from datetime import date, timedelta

from sqlalchemy import select, text

from db.read_cache import read_cached, table_names
from db.session_provenance import provenance, recorded_date, source_phase


@read_cached
def load_deload_exercise_ids(engine, *, as_of=None):
    from db.plan_schedule import links, sessions
    from db.recorded_workouts import actual_exercises

    as_of = as_of or date.today()
    with engine.connect() as connection:
        names = table_names(connection)
        required = {
            "training_plan_session_links",
            "training_plan_progression",
            "training_plan_days",
        }
        if not required.issubset(names):
            return frozenset()
        rows = (
            connection.execute(
                text("""
            SELECT l.day_id, d.version_id, d.name, l.scheduled_date, l.session_id,
                   s.session_date, p.block_start, p.block_weeks, we.workout_exercise_id
            FROM training_plan_session_links l
            JOIN training_plan_days d ON d.day_id=l.day_id
            JOIN training_plan_progression p ON p.version_id=d.version_id
            JOIN workout_sessions s ON s.session_id=l.session_id
            JOIN workout_exercises we ON we.session_id=l.session_id
        """)
            )
            .mappings()
            .all()
        )
        retained = (
            connection.execute(
                select(actual_exercises.c.workout_exercise_id)
                .join(provenance, provenance.c.session_id == actual_exercises.c.session_id)
                .join(sessions, sessions.c.session_id == actual_exercises.c.session_id)
                .where(
                    provenance.c.phase == "deload",
                    sessions.c.session_date < as_of + timedelta(days=1),
                    ~select(links.c.session_id)
                    .where(links.c.session_id == provenance.c.session_id)
                    .exists(),
                )
            )
            .scalars()
            .all()
            if provenance.name in names
            else ()
        )
    output = set(retained)
    for row in rows:
        performed = recorded_date(row["session_date"])
        if performed is None or performed > as_of:
            continue
        if (
            source_phase(row["scheduled_date"], performed, row["block_start"], row["block_weeks"])
            == "deload"
        ):
            output.add(row["workout_exercise_id"])
    return frozenset(output)
