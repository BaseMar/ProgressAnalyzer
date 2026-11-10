"""Base tables for a fresh installation; applied legacy migrations stay unchanged."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Time,
    UniqueConstraint,
    func,
)


def define_base_tables():
    metadata = MetaData()
    catalog = Table(
        "exercises",
        metadata,
        Column("exercise_id", Integer, primary_key=True),
        Column("exercise_name", String(200), nullable=False),
        Column("category", String(60)),
        Column("body_part", String(100)),
        CheckConstraint("length(trim(exercise_name)) > 0", name="ck_exercise_name"),
    )
    sessions = Table(
        "workout_sessions",
        metadata,
        Column("session_id", Integer, primary_key=True),
        Column("session_date", Date, nullable=False, index=True),
        Column("start_time", Time),
        Column("end_time", Time),
        Column("notes", String),
    )
    entries = Table(
        "workout_exercises",
        metadata,
        Column("workout_exercise_id", Integer, primary_key=True),
        Column(
            "session_id",
            ForeignKey(sessions.c.session_id, ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        Column(
            "exercise_id",
            ForeignKey(catalog.c.exercise_id, ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    Table(
        "workout_sets",
        metadata,
        Column("set_id", Integer, primary_key=True),
        Column(
            "workout_exercise_id",
            ForeignKey(entries.c.workout_exercise_id, ondelete="CASCADE"),
            nullable=False,
        ),
        Column("set_number", Integer, nullable=False),
        Column("repetitions", Integer, nullable=False, server_default="0"),
        Column("weight", Float, nullable=False, server_default="0"),
        Column("rir", Integer),
        Column("duration_seconds", Integer),
        UniqueConstraint("workout_exercise_id", "set_number", name="uq_workout_set_number"),
        CheckConstraint("set_number > 0", name="ck_workout_set_number"),
        CheckConstraint("repetitions >= 0 AND weight >= 0", name="ck_workout_set_values"),
        CheckConstraint("rir IS NULL OR rir >= 0", name="ck_workout_set_rir"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0", name="ck_workout_set_duration"
        ),
    )
    Table(
        "exercise_muscle_map",
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "exercise_id", ForeignKey(catalog.c.exercise_id, ondelete="CASCADE"), nullable=False
        ),
        Column("muscle_group", String(100), nullable=False),
        Column("muscle_name", String(200), nullable=False),
        Column("role", String(20), nullable=False),
        Column("set_factor", Float, nullable=False),
        Column("source_note", String),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
        UniqueConstraint("exercise_id", "muscle_group", name="uq_exercise_muscle_group"),
        CheckConstraint("role IN ('primary', 'secondary', 'stabilizer')", name="ck_muscle_role"),
        CheckConstraint("set_factor > 0 AND set_factor <= 1", name="ck_muscle_factor"),
    )
    Table(
        "body_composition",
        metadata,
        Column("measurement_id", Integer, primary_key=True),
        Column("measurement_date", DateTime, nullable=False, index=True),
        *(
            Column(name, Float)
            for name in ("weight", "muscle_mass", "fat_mass", "water_mass", "body_fat_percentage")
        ),
        Column("method", String(100)),
    )
    Table(
        "body_measurements",
        metadata,
        Column("measurement_id", Integer, primary_key=True),
        Column("measurement_date", DateTime, nullable=False, index=True),
        *(
            Column(name, Float)
            for name in ("chest", "waist", "abdomen", "hips", "thigh", "calf", "biceps")
        ),
    )
    return metadata
