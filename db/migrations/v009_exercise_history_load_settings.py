"""Store explicitly confirmed meanings of legacy bodyweight history."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Table

REVISION = "009_exercise_history_load_settings"


def define_table(metadata):
    return Table(
        "exercise_history_load_settings",
        metadata,
        Column(
            "exercise_id",
            Integer,
            ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column("legacy_bodyweight_is_body_mass", Boolean, nullable=False),
    )


def apply(connection):
    metadata = MetaData()
    Table("exercises", metadata, autoload_with=connection)
    define_table(metadata).create(connection)
