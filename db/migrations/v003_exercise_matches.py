"""User-confirmed replacements, scoped to one linked session and plan position."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, UniqueConstraint, func

REVISION = "003_exercise_matches"


def define_table(metadata):
    return Table("training_plan_exercise_matches", metadata,
        Column("session_id", Integer, ForeignKey("training_plan_session_links.session_id", ondelete="CASCADE"), primary_key=True),
        Column("plan_exercise_id", Integer, ForeignKey("training_plan_exercises.plan_exercise_id", ondelete="RESTRICT"), primary_key=True),
        Column("workout_exercise_id", Integer, ForeignKey("workout_exercises.workout_exercise_id", ondelete="CASCADE"), nullable=False),
        Column("confirmed_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
        UniqueConstraint("workout_exercise_id", name="uq_recorded_exercise_match"),
    )


def apply(connection):
    metadata = MetaData()
    for name in ("training_plan_session_links", "training_plan_exercises", "workout_exercises"):
        Table(name, metadata, autoload_with=connection)
    define_table(metadata).create(connection, checkfirst=False)
