"""Read exact-exercise history across plans without creating plan assignments."""

from datetime import date, time, timedelta

from sqlalchemy import select

from db.plan_schedule import sessions
from db.read_cache import read_cached
from db.recorded_workouts import actual_exercises, load_recorded_exercises
from db.session_provenance import (
    detached_session_provenance,
    linked_session_provenance,
    recorded_date,
)


@read_cached
def load_exercise_starting_history(engine, exercise_ids, *, as_of, plan_id=None):
    if type(as_of) is not date:
        raise ValueError("History cutoff must be a date")
    if not exercise_ids:
        return {}
    cutoff = as_of + timedelta(days=1)
    query = (
        select(
            actual_exercises,
            sessions.c.session_date,
            sessions.c.start_time,
        )
        .join(sessions, sessions.c.session_id == actual_exercises.c.session_id)
        .where(
            actual_exercises.c.exercise_id.in_(exercise_ids),
            sessions.c.session_date < cutoff,
        )
        .order_by(
            sessions.c.session_date.desc(),
            sessions.c.start_time.desc().nullslast(),
            sessions.c.session_id.desc(),
            actual_exercises.c.workout_exercise_id,
        )
    )
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
        session_ids = {row["session_id"] for row in rows}
        recorded = {
            item.workout_exercise_id: item
            for item in load_recorded_exercises(connection, session_ids, exercise_ids=exercise_ids)
        }
        linked = linked_session_provenance(connection, session_ids) if session_ids else {}
        detached = detached_session_provenance(
            connection, session_ids - linked.keys(), plan_id=plan_id, cutoff=cutoff
        )
        sources = linked | detached
    result = {}
    for row in rows:
        source = sources.get(row["session_id"], {})
        phase = source.get("phase", "unknown")
        if phase == "deload":
            continue
        targets = source.get("targets", ())
        matching = [
            target
            for target in targets
            if target["workout_exercise_id"] == row["workout_exercise_id"]
        ]
        if not matching:
            matching = [
                target
                for target in targets
                if target["workout_exercise_id"] is None
                and target["exercise_id"] == row["exercise_id"]
            ]
        result.setdefault(row["exercise_id"], []).append(
            {
                "session_id": row["session_id"],
                "date": recorded_date(row["session_date"]),
                "start_time": row["start_time"],
                "workout": source.get("workout"),
                "source_scheduled_date": source.get("scheduled_date"),
                "source_day_id": source.get("day_id"),
                "source_plan_matches": source.get(
                    "source_plan_matches", source.get("plan_id") == plan_id
                ),
                "source_workout_position": source.get("workout_position"),
                "training_phase": phase,
                "workout_exercise_id": row["workout_exercise_id"],
                "sets": recorded[row["workout_exercise_id"]].sets,
                "prescription": matching[0] if len(matching) == 1 else None,
            }
        )
    if plan_id is not None:
        present = {(row["session_id"], row["exercise_id"]) for row in rows}
        for session_id, source in detached.items():
            if not source["source_plan_matches"] or source["phase"] == "deload":
                continue
            for target in source["targets"]:
                exercise_id = target["exercise_id"]
                if (
                    exercise_id not in exercise_ids
                    or (session_id, exercise_id) in present
                    or target["workout_exercise_id"] is not None
                ):
                    continue
                result.setdefault(exercise_id, []).append(
                    {
                        "session_id": session_id,
                        "date": recorded_date(source["session_date"]),
                        "start_time": source["start_time"],
                        "workout": source["workout"],
                        "source_scheduled_date": source["scheduled_date"],
                        "source_day_id": source["day_id"],
                        "source_workout_position": source["workout_position"],
                        "training_phase": source["phase"],
                        "workout_exercise_id": None,
                        "sets": (),
                        "prescription": target,
                        "retained_omission": True,
                    }
                )
        for records in result.values():
            records.sort(
                key=lambda row: (
                    row["date"],
                    row["start_time"] is not None,
                    row["start_time"] or time.min,
                    row["session_id"],
                ),
                reverse=True,
            )
    return result
