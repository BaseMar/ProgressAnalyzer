"""Optional per-set load conventions; existing weights are never reinterpreted."""
from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, MetaData, String, Table

REVISION = "006_set_loads"


def define_table(metadata):
    return Table("workout_set_loads", metadata,
        Column("set_id", Integer, ForeignKey("workout_sets.set_id", ondelete="CASCADE"), primary_key=True, autoincrement=False),
        Column("load_type", String(30), nullable=False),
        Column("body_mass_kg", Float),
        Column("assistance_kg", Float),
        CheckConstraint("load_type IN ('external', 'bodyweight', 'assisted_bodyweight')", name="ck_set_load_type"),
        CheckConstraint("body_mass_kg IS NULL OR body_mass_kg > 0", name="ck_set_body_mass_positive"),
        CheckConstraint("assistance_kg IS NULL OR assistance_kg >= 0", name="ck_set_assistance_nonnegative"),
        CheckConstraint("load_type <> 'external' OR body_mass_kg IS NULL", name="ck_external_without_body_mass"),
        CheckConstraint("(load_type = 'assisted_bodyweight' AND (assistance_kg IS NULL OR assistance_kg > 0)) "
                        "OR (load_type <> 'assisted_bodyweight' AND assistance_kg IS NOT NULL AND assistance_kg = 0)",
                        name="ck_set_assistance_type"),
    )


def apply(connection):
    metadata = MetaData()
    Table("workout_sets", metadata, autoload_with=connection)
    define_table(metadata).create(connection, checkfirst=False)
