"""Optional explicit corrections; inferred meanings are never written here."""
import pandas as pd
from sqlalchemy import Column, Integer, MetaData, Table, select, text
from db.migrations.v004_set_classifications import define_table
from db.set_loads import load_sql_parts
from db.read_cache import has_table

metadata = MetaData()
sets = Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True), Column("workout_exercise_id", Integer))
workouts = Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True), Column("session_id", Integer))
classifications = define_table(metadata)


def classification_storage_ready(engine):
    with engine.connect() as connection:
        return has_table(connection, classifications.name)


def load_session_sets(engine, session_id):
    with engine.connect() as connection:
        load_columns, load_join = load_sql_parts(connection, "s")
        return pd.read_sql(text(f'''
            SELECT s.set_id, s.workout_exercise_id, e.exercise_name, s.set_number, s.repetitions, s.weight,
                   s.rir, s.duration_seconds, c.is_warmup, {load_columns}
            FROM workout_sets s JOIN workout_exercises we ON we.workout_exercise_id=s.workout_exercise_id
            JOIN exercises e ON e.exercise_id=we.exercise_id
            LEFT JOIN workout_set_classifications c ON c.set_id=s.set_id
            {load_join}
            WHERE we.session_id=:sid ORDER BY we.workout_exercise_id, s.set_number, s.set_id
        '''), connection, params={"sid": session_id})


def save_set_classifications(engine, session_id, values):
    if not all(type(key) is int and (value is None or type(value) is bool) for key, value in values.items()):
        raise ValueError("Set labels must be working, warm-up, or unknown")
    with engine.begin() as connection:
        allowed = set(connection.execute(select(sets.c.set_id).join(workouts, sets.c.workout_exercise_id == workouts.c.workout_exercise_id)
                      .where(workouts.c.session_id == session_id).with_for_update()).scalars())
        if not set(values).issubset(allowed):
            raise ValueError("One or more sets no longer belong to the selected session")
        connection.execute(classifications.delete().where(classifications.c.set_id.in_(values)))
        rows = [{"set_id": key, "is_warmup": value} for key, value in values.items() if value is not None]
        if rows:
            connection.execute(classifications.insert(), rows)
