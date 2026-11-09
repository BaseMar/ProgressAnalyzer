"""Explicit set labels; absent rows mean unknown, never inferred working sets."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Table

REVISION = "004_set_classifications"


def define_table(metadata):
    return Table(
        "workout_set_classifications",
        metadata,
        Column(
            "set_id",
            Integer,
            ForeignKey("workout_sets.set_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column("is_warmup", Boolean, nullable=False),
    )


def apply(connection):
    metadata = MetaData()
    Table("workout_sets", metadata, autoload_with=connection)
    define_table(metadata).create(connection, checkfirst=False)
