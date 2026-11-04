"""Load complete linked sessions across date filters and persist confirmations."""

from sqlalchemy import Column, Integer, Float, MetaData, Table, inspect, select
from sqlalchemy.exc import IntegrityError

from db.migrations.v003_exercise_matches import define_table
from db.plan_schedule import links, load_scheduled_workouts
from db.training_plans import exercises as targets
from metrics.plan_adherence import compatible_set
from models.plan_adherence import (
    ExerciseMatch, PlanAdherenceInput, PlannedTarget, PlannedWorkout, RecordedExercise,
)
from models.training_plan import PlannedExercise
from models.workout_set import WorkoutSet

metadata = MetaData()
Table("training_plan_session_links", metadata, Column("session_id", Integer, primary_key=True))
Table("training_plan_exercises", metadata, Column("plan_exercise_id", Integer, primary_key=True))
actual_exercises = Table("workout_exercises", metadata,
    Column("workout_exercise_id", Integer, primary_key=True),
    Column("session_id", Integer), Column("exercise_id", Integer),
)
actual_sets = Table("workout_sets", metadata,
    Column("workout_exercise_id", Integer), Column("set_number", Integer),
    Column("repetitions", Integer), Column("weight", Float),
    Column("rir", Integer), Column("duration_seconds", Integer),
)
matches = define_table(metadata)


def adherence_storage_ready(engine):
    with engine.connect() as connection:
        return inspect(connection).has_table(matches.name)


def _recorded(connection, session_ids):
    if not session_ids:
        return ()
    exercises = connection.execute(select(actual_exercises).where(actual_exercises.c.session_id.in_(session_ids))).mappings().all()
    rows = connection.execute(select(actual_sets).join(
        actual_exercises, actual_sets.c.workout_exercise_id == actual_exercises.c.workout_exercise_id,
    ).where(actual_exercises.c.session_id.in_(session_ids)).order_by(actual_sets.c.set_number)).mappings().all()
    sets = {row["workout_exercise_id"]: [] for row in exercises}
    for row in rows:
        sets[row["workout_exercise_id"]].append(WorkoutSet(
            row["workout_exercise_id"], row["set_number"], row["repetitions"] or 0,
            row["weight"] or 0., row["rir"], row["duration_seconds"],
        ))
    return tuple(RecordedExercise(row["workout_exercise_id"], row["session_id"], row["exercise_id"],
                                  tuple(sets[row["workout_exercise_id"]])) for row in exercises)


def load_plan_adherence(engine, plan_id, start, end) -> PlanAdherenceInput:
    slots = load_scheduled_workouts(engine, plan_id, start, end)
    day_ids = {slot.day_id for slot in slots}
    session_ids = {slot.session_id for slot in slots if slot.session_id is not None}
    with engine.connect() as connection:
        rows = connection.execute(select(targets).where(targets.c.day_id.in_(day_ids))
                                  .order_by(targets.c.position)).mappings().all() if day_ids else []
        by_day = {day_id: [] for day_id in day_ids}
        for row in rows:
            by_day[row["day_id"]].append(PlannedTarget(row["plan_exercise_id"], PlannedExercise(
                row["exercise_id"], row["set_count"], row["target_min"], row["target_max"],
                row["target_unit"], row["target_rir"], row["weight_increment"],
            )))
        recorded = _recorded(connection, session_ids)
        confirmed = tuple(ExerciseMatch(row.session_id, row.plan_exercise_id, row.workout_exercise_id)
                          for row in connection.execute(select(matches).where(matches.c.session_id.in_(session_ids)))) if session_ids else ()
    return PlanAdherenceInput(tuple(PlannedWorkout(slot, tuple(by_day[slot.day_id])) for slot in slots), recorded, confirmed)


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
