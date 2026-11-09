"""User-confirmed history semantics; never infer or rewrite legacy kilograms."""
from sqlalchemy import Column, Integer, MetaData, Table, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.migrations.v009_exercise_history_load_settings import define_table

metadata = MetaData()
Table('exercises', metadata, Column('exercise_id', Integer, primary_key=True))
history_load_settings = define_table(metadata)


def load_legacy_body_mass_exercise_ids(engine):
    with engine.connect() as connection:
        if not inspect(connection).has_table(history_load_settings.name):
            return frozenset()
        return frozenset(connection.execute(select(history_load_settings.c.exercise_id).where(
            history_load_settings.c.legacy_bodyweight_is_body_mass.is_(True))).scalars())


def confirm_legacy_body_mass_history(engine, exercise_id, *, confirmed=True):
    if type(exercise_id) is not int or exercise_id < 1 or type(confirmed) is not bool:
        raise ValueError('Choose a valid exercise and explicit confirmation')
    with engine.begin() as connection:
        insert = sqlite_insert if connection.dialect.name == 'sqlite' else pg_insert
        statement = insert(history_load_settings).values(exercise_id=exercise_id,
            legacy_bodyweight_is_body_mass=confirmed)
        connection.execute(statement.on_conflict_do_update(index_elements=[history_load_settings.c.exercise_id],
            set_={'legacy_bodyweight_is_body_mass': confirmed}))
