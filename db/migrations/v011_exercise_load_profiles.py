"""Remember exercise conventions and preserve originals before history normalization."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    func,
)

REVISION = "011_exercise_load_profiles"


def define_tables(metadata):
    profiles = Table(
        "exercise_load_profiles",
        metadata,
        Column(
            "exercise_id",
            Integer,
            ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column("load_type", String(30), nullable=False),
        Column("input_mode", String(30), nullable=False),
        Column("legacy_mode", String(30), nullable=False),
        Column("source", String(20), nullable=False),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
        CheckConstraint(
            "load_type IN ('external', 'bodyweight', 'assisted_bodyweight')",
            name="ck_profile_load_type",
        ),
        CheckConstraint("source IN ('catalog', 'history', 'user')", name="ck_profile_load_source"),
    )
    originals = Table(
        "workout_set_load_originals",
        metadata,
        Column(
            "set_id",
            Integer,
            ForeignKey("workout_sets.set_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column("weight", Float, nullable=False),
        Column("load_type", String(30)),
        Column("body_mass_kg", Float),
        Column("assistance_kg", Float),
        Column("normalized_weight", Float, nullable=False),
        Column("normalized_load_type", String(30), nullable=False),
        Column("normalized_body_mass_kg", Float),
        Column("normalized_assistance_kg", Float),
        Column(
            "normalized_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
    )
    return profiles, originals


def apply(connection):
    metadata = MetaData()
    Table("exercises", metadata, autoload_with=connection)
    Table("workout_sets", metadata, autoload_with=connection)
    profiles, originals = define_tables(metadata)
    profiles.create(connection)
    originals.create(connection)
