"""Explicit set-load corrections, saved atomically with the external weight."""
from datetime import date, datetime, timedelta
from math import isfinite

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, Table, inspect, select

from db.migrations.v006_set_loads import define_table
from models.set_load import SetLoad

metadata = MetaData()
sets = Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True),
             Column("workout_exercise_id", Integer), Column("weight", Float))
workouts = Table("workout_exercises", metadata, Column("workout_exercise_id", Integer, primary_key=True),
                 Column("session_id", Integer))
loads = define_table(metadata)
measurements = Table("body_composition", metadata,
    Column("measurement_date", DateTime), Column("weight", Float))


def suggest_body_mass(engine, on_date: date):
    """Return the latest valid mass on/before the workout, never a future value."""
    if type(on_date) is not date:
        raise ValueError("Workout date must be a date")
    with engine.connect() as connection:
        if not inspect(connection).has_table(measurements.name):
            return None
        rows = connection.execute(select(measurements.c.measurement_date, measurements.c.weight)
            .where(measurements.c.measurement_date < on_date + timedelta(days=1))
            .order_by(measurements.c.measurement_date.desc()))
        for measured_on, value in rows:
            if value is not None and isfinite(value) and value > 0:
                day = measured_on.date() if isinstance(measured_on, datetime) else measured_on
                return {"date": day, "weight": float(value)}
    return None


def insert_set_load(connection, set_id, value):
    """Persist an already validated load within its caller's transaction."""
    if not isinstance(value, SetLoad):
        raise ValueError("An explicit SetLoad is required")
    connection.execute(loads.insert().values(set_id=set_id, load_type=value.load_type,
        body_mass_kg=value.body_mass_kg, assistance_kg=value.assistance_kg))


def set_load_storage_ready(engine):
    with engine.connect() as connection:
        return inspect(connection).has_table(loads.name)


def load_sql_parts(connection, set_alias):
    """SQL fragments for internal, fixed set aliases; old schemas remain readable."""
    if inspect(connection).has_table(loads.name):
        return ("l.load_type, l.body_mass_kg, l.assistance_kg",
                f"LEFT JOIN workout_set_loads l ON l.set_id={set_alias}.set_id")
    return "NULL AS load_type, NULL AS body_mass_kg, NULL AS assistance_kg", ""


def save_session_set_loads(engine, session_id, values: dict[int, SetLoad | None]):
    """Replace explicit load records for selected sets within one session.

    None removes the convention while preserving the saved weight; it does not
    reconstruct a previous load. Existing unselected sets remain untouched.
    """
    if not all(type(key) is int and (value is None or isinstance(value, SetLoad))
               for key, value in values.items()):
        raise ValueError("Set loads must map integer set IDs to SetLoad values or None")
    if not values:
        return
    with engine.begin() as connection:
        if not inspect(connection).has_table(loads.name):
            raise ValueError("Set load storage needs migration 006_set_loads")
        allowed = set(connection.execute(select(sets.c.set_id).join(
            workouts, sets.c.workout_exercise_id == workouts.c.workout_exercise_id,
        ).where(workouts.c.session_id == session_id).with_for_update()).scalars())
        if not set(values).issubset(allowed):
            raise ValueError("One or more sets no longer belong to the selected session")
        connection.execute(loads.delete().where(loads.c.set_id.in_(values)))
        for set_id, value in values.items():
            if value is None:
                continue
            connection.execute(sets.update().where(sets.c.set_id == set_id).values(weight=value.external_weight_kg))
            insert_set_load(connection, set_id, value)
