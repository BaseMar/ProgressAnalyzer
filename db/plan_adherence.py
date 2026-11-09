"""Load complete linked sessions across date filters and persist confirmations."""

from dataclasses import replace
from datetime import date

from sqlalchemy import Column, Integer, Float, MetaData, String, Table, func, literal, select
from sqlalchemy.exc import IntegrityError

from db.migrations.v003_exercise_matches import define_table
from db.read_cache import has_table, read_cached
from db.plan_schedule import links, load_scheduled_workouts, sessions
from db.training_plans import exercises as targets, versions, days, exercise_lineage
from db.set_classifications import classifications
from db.set_loads import loads
from mapper import map_workout_set
from metrics.plan_adherence import compatible_set
from metrics.load_metrics import suggested_load_type
from models.plan_adherence import (
    ExerciseMatch, PlanAdherenceInput, PlannedTarget, PlannedWorkout, RecordedExercise,
)
from models.training_plan import PlannedExercise

metadata = MetaData()
Table("training_plan_session_links", metadata, Column("session_id", Integer, primary_key=True))
Table("training_plan_exercises", metadata, Column("plan_exercise_id", Integer, primary_key=True))
actual_exercises = Table("workout_exercises", metadata,
    Column("workout_exercise_id", Integer, primary_key=True),
    Column("session_id", Integer), Column("exercise_id", Integer),
)
actual_sets = Table("workout_sets", metadata,
    Column("set_id", Integer, primary_key=True),
    Column("workout_exercise_id", Integer), Column("set_number", Integer),
    Column("repetitions", Integer), Column("weight", Float),
    Column("rir", Integer), Column("duration_seconds", Integer),
)
catalog_exercises = Table("exercises", metadata, Column("exercise_id", Integer, primary_key=True),
                          Column("exercise_name", String))
matches = define_table(metadata)


def adherence_storage_ready(engine):
    with engine.connect() as connection:
        return has_table(connection, matches.name)


@read_cached
def _recorded(connection, session_ids, *, exercise_ids=None):
    if not session_ids:
        return ()
    exercise_filter = [actual_exercises.c.session_id.in_(session_ids)]
    if exercise_ids is not None:
        exercise_filter.append(actual_exercises.c.exercise_id.in_(exercise_ids))
    exercises = connection.execute(select(actual_exercises).where(*exercise_filter)).mappings().all()
    load_fields = ("load_type", "body_mass_kg", "assistance_kg")
    load_storage = has_table(connection, loads.name)
    columns = [loads.c[name] if load_storage else literal(None).label(name) for name in load_fields]
    query = select(actual_sets, classifications.c.is_warmup, *columns).outerjoin(
        classifications, classifications.c.set_id == actual_sets.c.set_id,
    ).join(
        actual_exercises, actual_sets.c.workout_exercise_id == actual_exercises.c.workout_exercise_id,
    )
    if load_storage:
        query = query.outerjoin(loads, loads.c.set_id == actual_sets.c.set_id)
    rows = connection.execute(query.where(*exercise_filter)
                              .order_by(actual_sets.c.set_number)).mappings().all()
    sets = {row["workout_exercise_id"]: [] for row in exercises}
    for row in rows:
        sets[row["workout_exercise_id"]].append(map_workout_set({
            **row, "repetitions": row["repetitions"] or 0, "weight": row["weight"] or 0.,
        }))
    return tuple(RecordedExercise(row["workout_exercise_id"], row["session_id"], row["exercise_id"],
                                  tuple(sets[row["workout_exercise_id"]])) for row in exercises)


@read_cached
def _plan_targets(engine, plan_id):
    with engine.connect() as connection:
        rows = connection.execute(select(targets).join(days, targets.c.day_id == days.c.day_id)
            .join(versions, days.c.version_id == versions.c.version_id).where(
            versions.c.plan_id == plan_id).order_by(targets.c.position)).mappings().all()
        by_day = {}
        lineage = dict(connection.execute(select(exercise_lineage.c.plan_exercise_id, exercise_lineage.c.history_key)
            .where(exercise_lineage.c.plan_exercise_id.in_([row["plan_exercise_id"] for row in rows]))).all()) if (
                rows and has_table(connection, exercise_lineage.name)) else {}
        for row in rows:
            by_day.setdefault(row["day_id"], []).append(PlannedTarget(row["plan_exercise_id"], PlannedExercise(
                row["exercise_id"], row["set_count"], row["target_min"], row["target_max"],
                row["target_unit"], row["target_rir"], row["weight_increment"],
                history_key=lineage.get(row["plan_exercise_id"]),
            )))
    return by_day


@read_cached
def _confirmed(connection, session_ids):
    return tuple(ExerciseMatch(row.session_id, row.plan_exercise_id, row.workout_exercise_id)
                 for row in connection.execute(select(matches).where(matches.c.session_id.in_(session_ids)))) if session_ids else ()


@read_cached
def _manual_load_ids(connection):
    return frozenset(row.exercise_id for row in connection.execute(
        select(catalog_exercises.c.exercise_id, catalog_exercises.c.exercise_name))
        if suggested_load_type(row.exercise_name) in ("bodyweight", "assisted_bodyweight"))


@read_cached
def load_plan_adherence(engine, plan_id, start, end) -> PlanAdherenceInput:
    slots = load_scheduled_workouts(engine, plan_id, start, end)
    session_ids = {slot.session_id for slot in slots if slot.session_id is not None}
    by_day = _plan_targets(engine, plan_id) if slots else {}
    with engine.connect() as connection:
        recorded = _recorded(connection, session_ids)
        confirmed = _confirmed(connection, session_ids)
        manual_ids = _manual_load_ids(connection)
    return PlanAdherenceInput(tuple(PlannedWorkout(slot, tuple(by_day.get(slot.day_id, ()))) for slot in slots),
                              recorded, confirmed, manual_load_exercise_ids=manual_ids)


@read_cached
def _performance_bounds(engine, plan_id):
    with engine.connect() as connection:
        first = connection.execute(select(func.min(versions.c.effective_from)).where(
            versions.c.plan_id == plan_id,
        )).scalar_one()
        last_linked = connection.execute(select(func.max(links.c.scheduled_date)).join(
            days, links.c.day_id == days.c.day_id,
        ).join(versions, days.c.version_id == versions.c.version_id).where(
            versions.c.plan_id == plan_id,
        )).scalar_one()
    return first, last_linked


@read_cached
def _session_order(connection, ids):
    return tuple(connection.execute(select(sessions.c.session_id).where(sessions.c.session_id.in_(ids))
                 .order_by(sessions.c.session_date, sessions.c.start_time.asc().nullsfirst(), sessions.c.session_id)).scalars()) if ids else ()


@read_cached
def load_plan_performance(engine, plan_id, start, end) -> PlanAdherenceInput:
    """Include earlier linked workouts, independently of the visible month.

    Include linked future slots too: a workout may have been recorded early.
    Comparisons are ordered by actual session date/time, never planned date.
    """
    first, last_linked = _performance_bounds(engine, plan_id)
    data = load_plan_adherence(engine, plan_id, min(start, first or start), max(end, date.today(), last_linked or end))
    ids = {item.slot.session_id for item in data.workouts if item.slot.session_id is not None}
    with engine.connect() as connection:
        order = _session_order(connection, ids)
    return replace(data, session_order=order)


def save_exercise_match(engine, session_id, plan_exercise_id, workout_exercise_id):
    try:
        with engine.begin() as connection:
            assignment = connection.execute(select(links).where(links.c.session_id == session_id)
                                            .with_for_update()).mappings().one_or_none()
            if assignment is None:
                raise ValueError("Link the recorded session to a planned workout first")
            planned = connection.execute(select(targets).where(
                targets.c.plan_exercise_id == plan_exercise_id,
                targets.c.day_id == assignment["day_id"],
            )).mappings().one_or_none()
            actual = next((item for item in _recorded(connection, [session_id])
                           if item.workout_exercise_id == workout_exercise_id), None)
            if planned is None or actual is None:
                raise ValueError("Choose a planned position and an exercise from its linked session")
            if not any(compatible_set(item, planned["target_unit"]) for item in actual.sets):
                raise ValueError("The replacement has no recorded sets with the planned unit")
            connection.execute(matches.delete().where(matches.c.session_id == session_id,
                                                       matches.c.plan_exercise_id == plan_exercise_id))
            connection.execute(matches.insert().values(session_id=session_id, plan_exercise_id=plan_exercise_id,
                                                        workout_exercise_id=workout_exercise_id))
    except IntegrityError as exc:
        raise ValueError("This recorded exercise already covers another planned position") from exc


def remove_exercise_match(engine, session_id, plan_exercise_id):
    with engine.begin() as connection:
        connection.execute(matches.delete().where(matches.c.session_id == session_id,
                                                   matches.c.plan_exercise_id == plan_exercise_id))
