"""Resolve remembered exercise conventions without changing historical set records."""

from datetime import date, timedelta

from sqlalchemy import Column, Integer, MetaData, String, Table, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.migrations.v011_exercise_load_profiles import define_tables
from db.read_cache import has_table, read_cached
from db.recorded_workouts import actual_exercises, actual_sets
from db.set_loads import loads
from metrics.load_profiles import resolve_exercise_load_profile
from models.load_profile import ExerciseLoadProfile

metadata = MetaData()
catalog = Table(
    "exercises",
    metadata,
    Column("exercise_id", Integer, primary_key=True),
    Column("exercise_name", String),
)
Table("workout_sets", metadata, Column("set_id", Integer, primary_key=True))
profiles, originals = define_tables(metadata)
sessions = Table(
    "workout_sessions",
    MetaData(),
    Column("session_id", Integer, primary_key=True),
    Column("session_date", String),
)


def profile_storage_ready(engine):
    with engine.connect() as connection:
        return has_table(connection, profiles.name) and has_table(connection, originals.name)


def resolved_profiles(connection, *, on_date, exercise_ids=None):
    query = select(catalog)
    if exercise_ids is not None:
        query = query.where(catalog.c.exercise_id.in_(exercise_ids))
    exercises = connection.execute(query).mappings().all()
    ids = [row["exercise_id"] for row in exercises]
    saved = {}
    if ids and has_table(connection, profiles.name):
        saved = {
            row["exercise_id"]: ExerciseLoadProfile(
                **{
                    key: row[key]
                    for key in ("exercise_id", "load_type", "input_mode", "legacy_mode", "source")
                }
            )
            for row in connection.execute(
                select(profiles).where(profiles.c.exercise_id.in_(ids))
            ).mappings()
        }
    history = {}
    if ids and has_table(connection, loads.name):
        rows = connection.execute(
            select(actual_exercises.c.exercise_id, loads.c.load_type)
            .distinct()
            .join(
                actual_sets,
                actual_sets.c.workout_exercise_id == actual_exercises.c.workout_exercise_id,
            )
            .join(loads, loads.c.set_id == actual_sets.c.set_id)
            .join(sessions, sessions.c.session_id == actual_exercises.c.session_id)
            .where(
                actual_exercises.c.exercise_id.in_(ids),
                sessions.c.session_date < str(on_date + timedelta(days=1)),
            )
        )
        for row in rows:
            history.setdefault(row.exercise_id, set()).add(row.load_type)
    confirmed = set()
    from db.exercise_history_load_settings import history_load_settings

    if ids and has_table(connection, history_load_settings.name):
        confirmed = set(
            connection.execute(
                select(history_load_settings.c.exercise_id).where(
                    history_load_settings.c.exercise_id.in_(ids),
                    history_load_settings.c.legacy_bodyweight_is_body_mass.is_(True),
                )
            ).scalars()
        )
    return {
        row["exercise_id"]: resolve_exercise_load_profile(
            row["exercise_id"],
            row["exercise_name"],
            saved=saved.get(row["exercise_id"]),
            history=history.get(row["exercise_id"], ()),
            body_mass_confirmed=row["exercise_id"] in confirmed,
        )
        for row in exercises
    }


@read_cached
def load_profile_catalog(engine):
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(select(catalog)).mappings()]


@read_cached
def load_resolved_profiles(engine, *, on_date=None, exercise_ids=None):
    with engine.connect() as connection:
        return resolved_profiles(
            connection, on_date=on_date or date.today(), exercise_ids=exercise_ids
        )


def store_profile(connection, profile):
    if not isinstance(profile, ExerciseLoadProfile):
        raise ValueError("A validated exercise load profile is required")
    insert = sqlite_insert if connection.dialect.name == "sqlite" else pg_insert
    statement = insert(profiles).values(
        exercise_id=profile.exercise_id,
        load_type=profile.load_type,
        input_mode=profile.input_mode,
        legacy_mode=profile.legacy_mode,
        source=profile.source,
    )
    connection.execute(
        statement.on_conflict_do_update(
            index_elements=["exercise_id"],
            set_={
                **{
                    key: getattr(statement.excluded, key)
                    for key in ("load_type", "input_mode", "legacy_mode", "source")
                },
                "updated_at": func.current_timestamp(),
            },
        )
    )


def save_profile(engine, profile):
    with engine.begin() as connection:
        if not has_table(connection, profiles.name):
            raise ValueError("Exercise load settings need database migration 011")
        store_profile(connection, profile)


def load_original_set_load(engine, set_id):
    with engine.connect() as connection:
        if not has_table(connection, originals.name):
            return None
        row = (
            connection.execute(select(originals).where(originals.c.set_id == set_id))
            .mappings()
            .first()
        )
        return dict(row) if row else None


def restore_original_set_load(engine, session_id, set_id):
    with engine.begin() as connection:
        original = (
            connection.execute(select(originals).where(originals.c.set_id == set_id))
            .mappings()
            .one_or_none()
        )
        if original is None:
            raise ValueError("This set has no archived normalization")
        current = connection.execute(
            select(
                actual_sets.c.weight, loads.c.load_type, loads.c.body_mass_kg, loads.c.assistance_kg
            )
            .join(
                actual_exercises,
                actual_exercises.c.workout_exercise_id == actual_sets.c.workout_exercise_id,
            )
            .outerjoin(loads, loads.c.set_id == actual_sets.c.set_id)
            .where(actual_sets.c.set_id == set_id, actual_exercises.c.session_id == session_id)
        ).one_or_none()
        if current is None:
            raise ValueError("The set does not belong to this session")
        keys = ("weight", "load_type", "body_mass_kg", "assistance_kg")
        before = tuple(original[key] for key in keys)
        applied = tuple(original["normalized_" + key] for key in keys)
        if tuple(current) == before:
            return False
        if tuple(current) != applied:
            raise ValueError(
                "This set was edited after normalization; review its current values before restoring"
            )
        connection.execute(loads.delete().where(loads.c.set_id == set_id))
        connection.execute(
            actual_sets.update()
            .where(actual_sets.c.set_id == set_id)
            .values(weight=original["weight"])
        )
        if original["load_type"] is not None:
            connection.execute(
                loads.insert().values(
                    **{
                        key: original[key]
                        for key in ("set_id", "load_type", "body_mass_kg", "assistance_kg")
                    }
                )
            )
    return True
