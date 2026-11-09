"""Explicit set-load corrections, saved atomically with the external weight."""
from datetime import date
from math import isfinite

import pandas as pd
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, cast, select

from db.migrations.v006_set_loads import define_table
from db.read_cache import has_table
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
        if not has_table(connection, measurements.name):
            return None
        # Legacy installations store dates as TEXT; newer schemas use DATE or
        # TIMESTAMP. Normalize this small measurement history without imposing
        # a date operator on the physical column or changing historical records.
        rows = connection.execute(select(cast(measurements.c.measurement_date, String), measurements.c.weight))
        latest = None
        for measured_on, raw_weight in rows:
            try:
                stamp = pd.Timestamp(measured_on)
                weight = float(raw_weight)
                if pd.isna(stamp) or not isfinite(weight) or weight <= 0 or stamp.date() > on_date:
                    continue
                stamp = stamp.tz_localize(None)
            except (ValueError, TypeError, OverflowError):
                continue
            if latest is None or stamp > latest[0]:
                latest = stamp, weight
    return {"date": latest[0].date(), "weight": latest[1]} if latest is not None else None


def insert_set_load(connection, set_id, value):
    """Persist an already validated load within its caller's transaction."""
    if not isinstance(value, SetLoad):
        raise ValueError("An explicit SetLoad is required")
    connection.execute(loads.insert().values(set_id=set_id, load_type=value.load_type,
        body_mass_kg=value.body_mass_kg, assistance_kg=value.assistance_kg))


def set_load_storage_ready(engine):
    with engine.connect() as connection:
        return has_table(connection, loads.name)


def load_sql_parts(connection, set_alias):
    """SQL fragments for internal, fixed set aliases; old schemas remain readable."""
    if has_table(connection, loads.name):
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
        if not has_table(connection, loads.name):
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
