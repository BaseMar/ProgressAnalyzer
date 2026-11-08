"""Stable plan-position lineage without changing recorded performances."""
from collections import Counter

from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, select

REVISION = "007_recommendation_lineage"


def define_table(metadata):
    return Table("training_plan_exercise_lineage", metadata,
        Column("plan_exercise_id", Integer,
               ForeignKey("training_plan_exercises.plan_exercise_id", ondelete="CASCADE"),
               primary_key=True, autoincrement=False),
        Column("history_key", String(160), nullable=False),
    )


def legacy_key(plan_id, workout_position, exercise_id, occurrence):
    return f"plan:{plan_id}:workout:{workout_position}:exercise:{exercise_id}:occurrence:{occurrence}"


def apply(connection):
    metadata = MetaData()
    versions = Table("training_plan_versions", metadata, autoload_with=connection)
    days = Table("training_plan_days", metadata, autoload_with=connection)
    targets = Table("training_plan_exercises", metadata, autoload_with=connection)
    lineage = define_table(metadata)
    lineage.create(connection)
    rows = connection.execute(select(
        targets.c.plan_exercise_id, targets.c.exercise_id, targets.c.day_id,
        days.c.position.label("workout_position"), versions.c.plan_id,
    ).join(days, targets.c.day_id == days.c.day_id)
      .join(versions, days.c.version_id == versions.c.version_id)
      .order_by(targets.c.day_id, targets.c.position)).mappings()
    occurrences = Counter()
    values = []
    for row in rows:
        group = (row["day_id"], row["exercise_id"])
        occurrences[group] += 1
        values.append(dict(plan_exercise_id=row["plan_exercise_id"], history_key=legacy_key(
            row["plan_id"], row["workout_position"], row["exercise_id"], occurrences[group])))
    if values:
        connection.execute(lineage.insert(), values)
