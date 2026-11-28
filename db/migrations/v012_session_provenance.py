"""Keep established training context independently of the calendar link."""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)

REVISION = "012_session_provenance"


def define_table(metadata):
    return Table(
        "workout_session_provenance",
        metadata,
        Column(
            "session_id",
            ForeignKey("workout_sessions.session_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        Column("plan_id", Integer, nullable=False, index=True),
        Column("plan_created_at", DateTime(timezone=True), nullable=False),
        Column("version_id", Integer, nullable=False),
        Column("day_id", Integer, nullable=False),
        Column("scheduled_date", Date, nullable=False),
        Column("workout", String, nullable=False),
        Column("workout_position", Integer, nullable=False),
        Column("phase", String(12), nullable=False),
        Column("targets", JSON, nullable=False),
        CheckConstraint(
            "phase IN ('normal', 'deload', 'unknown')", name="ck_session_provenance_phase"
        ),
    )


def apply(connection):
    from db.session_provenance import preserve_session_provenance

    metadata = MetaData()
    Table("workout_sessions", metadata, autoload_with=connection)
    define_table(metadata).create(connection)
    preserve_session_provenance(connection)
