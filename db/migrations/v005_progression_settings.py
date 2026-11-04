"""Versioned block configuration; legacy plans remain unconfigured."""
from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, Integer, MetaData, Table

REVISION = "005_progression_settings"


def define_table(metadata):
    return Table("training_plan_progression", metadata,
        Column("version_id", Integer, ForeignKey("training_plan_versions.version_id", ondelete="RESTRICT"), primary_key=True, autoincrement=False),
        Column("block_start", Date, nullable=False),
        Column("block_weeks", Integer, nullable=False),
        CheckConstraint("block_weeks IN (6, 7, 8)", name="ck_progression_block_weeks"),
    )


def apply(connection):
    metadata = MetaData()
    Table("training_plan_versions", metadata, autoload_with=connection)
    define_table(metadata).create(connection, checkfirst=False)
