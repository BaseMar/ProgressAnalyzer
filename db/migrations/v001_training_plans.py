"""Initial plan schema; only creates new tables, preserving workout history."""

from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Integer,
    MetaData, String, Table, UniqueConstraint, func,
)

REVISION = "001_training_plans"


def define_tables(metadata: MetaData) -> dict[str, Table]:
    # The existing exercises table must be reflected into metadata by the caller.
    plans = Table("training_plans", metadata,
        Column("plan_id", Integer, primary_key=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
    )
    versions = Table("training_plan_versions", metadata,
        Column("version_id", Integer, primary_key=True),
        Column("plan_id", Integer, ForeignKey(plans.c.plan_id, ondelete="RESTRICT"), nullable=False),
        Column("version_number", Integer, nullable=False),
        Column("name", String(120), nullable=False),
        Column("effective_from", Date, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
        CheckConstraint("version_number > 0", name="ck_plan_version_positive"),
        CheckConstraint("length(trim(name)) > 0", name="ck_plan_name"),
        UniqueConstraint("plan_id", "version_number", name="uq_plan_version_number"),
        UniqueConstraint("plan_id", "effective_from", name="uq_plan_effective_date"),
    )
    days = Table("training_plan_days", metadata,
        Column("day_id", Integer, primary_key=True),
        Column("version_id", Integer, ForeignKey(versions.c.version_id, ondelete="RESTRICT"), nullable=False),
        Column("name", String(120), nullable=False),
        Column("weekday", Integer, nullable=False),
        Column("position", Integer, nullable=False),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_plan_weekday"),
        CheckConstraint("position > 0", name="ck_plan_day_position"),
        CheckConstraint("length(trim(name)) > 0", name="ck_plan_day_name"),
        UniqueConstraint("version_id", "position", name="uq_plan_day_position"),
    )
    exercises = Table("training_plan_exercises", metadata,
        Column("plan_exercise_id", Integer, primary_key=True),
        Column("day_id", Integer, ForeignKey(days.c.day_id, ondelete="RESTRICT"), nullable=False),
        Column("exercise_id", Integer, ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False),
        Column("position", Integer, nullable=False),
        Column("set_count", Integer, nullable=False),
        Column("target_min", Integer, nullable=False),
        Column("target_max", Integer, nullable=False),
        Column("target_unit", String(10), nullable=False),
        Column("target_rir", Integer),
        Column("weight_increment", Float),
        CheckConstraint("position > 0", name="ck_plan_exercise_position"),
        CheckConstraint("set_count > 0", name="ck_plan_sets"),
        CheckConstraint("target_min > 0 AND target_max >= target_min", name="ck_plan_target_range"),
        CheckConstraint("target_unit IN ('reps', 'seconds')", name="ck_plan_target_unit"),
        CheckConstraint("target_rir IS NULL OR target_rir >= 0", name="ck_plan_rir"),
        CheckConstraint("weight_increment IS NULL OR weight_increment > 0", name="ck_plan_increment"),
        UniqueConstraint("day_id", "position", name="uq_plan_exercise_position"),
    )
    return {table.name: table for table in (plans, versions, days, exercises)}


def apply(connection) -> None:
    metadata = MetaData()
    Table("exercises", metadata, autoload_with=connection)
    tables = define_tables(metadata)
    metadata.create_all(connection, tables=list(tables.values()), checkfirst=False)
