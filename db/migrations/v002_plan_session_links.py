"""One explicit session assignment per scheduled workout, across all plans."""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    UniqueConstraint,
    func,
)

REVISION = "002_plan_session_links"


def define_table(metadata):
    return Table(
        "training_plan_session_links",
        metadata,
        Column(
            "session_id",
            Integer,
            ForeignKey("workout_sessions.session_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column(
            "day_id",
            Integer,
            ForeignKey("training_plan_days.day_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("scheduled_date", Date, nullable=False),
        Column(
            "linked_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
        UniqueConstraint("day_id", "scheduled_date", name="uq_scheduled_workout_link"),
    )


def apply(connection):
    metadata = MetaData()
    Table("training_plan_days", metadata, autoload_with=connection)
    Table("workout_sessions", metadata, autoload_with=connection)
    define_table(metadata).create(connection, checkfirst=False)
