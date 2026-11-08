"""Read-only source records for manual starts, separate from progression evidence."""
from datetime import date

from sqlalchemy import func, select

from db.plan_adherence import _recorded, actual_exercises
from db.plan_schedule import links, sessions
from db.training_plans import days


def load_recommendation_references(engine, exercise_ids, *, as_of):
    """Show the latest session even before the plan/block or without a link.

    Keep repeated exercise entries separate. These records never enter the
    recommendation engine or establish automatic progression eligibility.
    """
    if type(as_of) is not date:
        raise ValueError("Reference cutoff must be a date")
    if not exercise_ids:
        return {}
    ranked = select(actual_exercises, sessions.c.session_date,
        func.dense_rank().over(partition_by=actual_exercises.c.exercise_id,
            order_by=(sessions.c.session_date.desc(), sessions.c.start_time.desc().nullslast(),
                      sessions.c.session_id.desc())).label("recency")
    ).join(sessions, sessions.c.session_id == actual_exercises.c.session_id).where(
        actual_exercises.c.exercise_id.in_(exercise_ids), sessions.c.session_date <= as_of).subquery()
    with engine.connect() as connection:
        rows = connection.execute(select(ranked, days.c.name.label("workout"))
            .outerjoin(links, links.c.session_id == ranked.c.session_id)
            .outerjoin(days, days.c.day_id == links.c.day_id)
            .where(ranked.c.recency == 1).order_by(ranked.c.workout_exercise_id)).mappings().all()
        records = {item.workout_exercise_id: item for item in _recorded(
            connection, {row["session_id"] for row in rows})}
    result = {}
    for row in rows:
        result.setdefault(row["exercise_id"], []).append({
            "session_id": row["session_id"], "date": row["session_date"],
            "workout": row["workout"], "workout_exercise_id": row["workout_exercise_id"],
            "sets": records[row["workout_exercise_id"]].sets,
        })
    return result
