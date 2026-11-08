"""Transactional plan snapshots. Revisions append rows; they never edit history."""

from datetime import date
from collections import Counter
from uuid import uuid4

from sqlalchemy import Column, Integer, MetaData, Table, func, inspect, select

from db.migrations.v001_training_plans import define_tables
from db.migrations.v005_progression_settings import define_table
from db.migrations.v007_recommendation_lineage import define_table as define_lineage, legacy_key
from models.training_plan import PlannedExercise, ProgressionSettings, TrainingDay, TrainingPlanDraft, TrainingPlanVersion

metadata = MetaData()
Table("exercises", metadata, Column("exercise_id", Integer, primary_key=True))
tables = define_tables(metadata)
plans = tables["training_plans"]
versions = tables["training_plan_versions"]
days = tables["training_plan_days"]
exercises = tables["training_plan_exercises"]
progression_settings = define_table(metadata)
exercise_lineage = define_lineage(metadata)


def training_plan_storage_ready(engine) -> bool:
    """Check availability without creating or modifying tables."""
    with engine.connect() as connection:
        return (set(tables) | {progression_settings.name}).issubset(inspect(connection).get_table_names())


def _load_progression(connection, version_id):
    row = connection.execute(select(progression_settings).where(
        progression_settings.c.version_id == version_id,
    )).mappings().one_or_none()
    return ProgressionSettings(row["block_start"], row["block_weeks"]) if row else None


def save_training_plan(engine, draft: TrainingPlanDraft, *, plan_id: int | None = None) -> TrainingPlanVersion:
    """Create a plan or append its next version atomically.

    Revision dates must follow the latest saved version and cannot be in the
    past. The next effective date implicitly ends the previous version.
    Existing workouts are never assigned to a plan by this operation.
    Omitted progression settings on a revision inherit the previous snapshot;
    only explicit settings change a configured block's start date or length.
    """
    if not isinstance(draft, TrainingPlanDraft):
        raise ValueError("A validated TrainingPlanDraft is required")
    with engine.begin() as connection:
        version_number = 1
        settings = draft.progression
        if plan_id is None:
            plan_id = connection.execute(plans.insert().values()).inserted_primary_key[0]
        else:
            locked = connection.execute(
                select(plans.c.plan_id).where(plans.c.plan_id == plan_id).with_for_update()
            ).scalar_one_or_none()
            if locked is None:
                raise ValueError("Training plan not found")
            latest = connection.execute(
                select(versions).where(versions.c.plan_id == plan_id)
                .order_by(versions.c.version_number.desc()).limit(1)
            ).mappings().one()
            if settings is None:
                settings = _load_progression(connection, latest["version_id"])
            if draft.effective_from <= latest["effective_from"] or draft.effective_from < date.today():
                raise ValueError("New version must start after the previous version and cannot be backdated")
            from db.plan_schedule import links
            if inspect(connection).has_table(links.name):
                linked_future = connection.execute(
                    select(links.c.session_id).join(days, links.c.day_id == days.c.day_id)
                    .join(versions, days.c.version_id == versions.c.version_id).where(
                        versions.c.plan_id == plan_id, links.c.scheduled_date >= draft.effective_from,
                    ).limit(1)
                ).first()
                if linked_future is not None:
                    raise ValueError("This version would replace an already linked workout. Remove its link or choose a later start date.")
            version_number = latest["version_number"] + 1
        version_id = connection.execute(versions.insert().values(
            plan_id=plan_id, version_number=version_number,
            name=draft.name.strip(), effective_from=draft.effective_from,
        )).inserted_primary_key[0]
        if settings is not None:
            connection.execute(progression_settings.insert().values(
                version_id=version_id, block_start=settings.block_start, block_weeks=settings.block_weeks,
            ))
        used_history_keys = set()
        for position, day in enumerate(draft.days, start=1):
            day_id = connection.execute(days.insert().values(
                version_id=version_id, name=day.name.strip(), weekday=day.weekday, position=position,
            )).inserted_primary_key[0]
            rows = [dict(
                day_id=day_id, position=index, exercise_id=item.exercise_id,
                set_count=item.set_count, target_min=item.target_min,
                target_max=item.target_max, target_unit=item.target_unit,
                target_rir=item.target_rir, weight_increment=item.weight_increment,
            ) for index, item in enumerate(day.exercises, start=1)]
            if inspect(connection).has_table(exercise_lineage.name):
                occurrences = Counter()
                for item, values in zip(day.exercises, rows):
                    occurrences[item.exercise_id] += 1
                    target_id = connection.execute(exercises.insert().values(**values)).inserted_primary_key[0]
                    key = item.history_key or legacy_key(plan_id, position, item.exercise_id, occurrences[item.exercise_id])
                    if key in used_history_keys:
                        if item.history_key:
                            raise ValueError("A plan position cannot share its history key with another position")
                        key = f"plan:{plan_id}:position:{uuid4().hex}"
                    used_history_keys.add(key)
                    connection.execute(exercise_lineage.insert().values(plan_exercise_id=target_id, history_key=key))
            else:
                connection.execute(exercises.insert(), rows)
        return _load_version(connection, version_id)


def _load_version(connection, version_id: int) -> TrainingPlanVersion | None:
    version = connection.execute(
        select(versions).where(versions.c.version_id == version_id)
    ).mappings().one_or_none()
    if version is None:
        return None
    day_rows = connection.execute(
        select(days).where(days.c.version_id == version_id).order_by(days.c.position)
    ).mappings().all()
    exercise_rows = connection.execute(
        select(exercises).join(days, exercises.c.day_id == days.c.day_id)
        .where(days.c.version_id == version_id).order_by(days.c.position, exercises.c.position)
    ).mappings().all()
    items_by_day = {day["day_id"]: [] for day in day_rows}
    lineage = dict(connection.execute(select(exercise_lineage.c.plan_exercise_id, exercise_lineage.c.history_key)
        .where(exercise_lineage.c.plan_exercise_id.in_([row["plan_exercise_id"] for row in exercise_rows]))).all()) if (
            exercise_rows and inspect(connection).has_table(exercise_lineage.name)) else {}
    for row in exercise_rows:
        items_by_day[row["day_id"]].append(PlannedExercise(
            exercise_id=row["exercise_id"], set_count=row["set_count"],
            target_min=row["target_min"], target_max=row["target_max"],
            target_unit=row["target_unit"], target_rir=row["target_rir"],
            weight_increment=row["weight_increment"],
            history_key=lineage.get(row["plan_exercise_id"]),
        ))
    return TrainingPlanVersion(
        plan_id=version["plan_id"], version_id=version_id,
        version_number=version["version_number"],
        draft=TrainingPlanDraft(version["name"], version["effective_from"], tuple(
            TrainingDay(day["name"], day["weekday"], tuple(items_by_day[day["day_id"]]))
            for day in day_rows
        ), progression=_load_progression(connection, version_id)),
    )


def load_training_plan_version(engine, version_id: int) -> TrainingPlanVersion | None:
    with engine.connect() as connection:
        return _load_version(connection, version_id)


def load_effective_training_plan(engine, plan_id: int, on_date: date) -> TrainingPlanVersion | None:
    """Resolve the snapshot applicable on a date, excluding future revisions."""
    with engine.connect() as connection:
        version_id = connection.execute(
            select(versions.c.version_id).where(
                versions.c.plan_id == plan_id, versions.c.effective_from <= on_date,
            ).order_by(versions.c.effective_from.desc()).limit(1)
        ).scalar_one_or_none()
        return _load_version(connection, version_id) if version_id is not None else None


def load_training_plan_versions(engine, plan_id: int) -> list[TrainingPlanVersion]:
    with engine.connect() as connection:
        ids = connection.execute(
            select(versions.c.version_id).where(versions.c.plan_id == plan_id)
            .order_by(versions.c.version_number)
        ).scalars().all()
        return [_load_version(connection, version_id) for version_id in ids]


def load_training_plans(engine) -> list[TrainingPlanVersion]:
    """List each plan's latest saved snapshot, including future versions."""
    latest = select(
        versions.c.plan_id, func.max(versions.c.version_number).label("number"),
    ).group_by(versions.c.plan_id).subquery()
    with engine.connect() as connection:
        ids = connection.execute(select(versions.c.version_id).join(latest,
            (versions.c.plan_id == latest.c.plan_id) & (versions.c.version_number == latest.c.number),
        ).order_by(versions.c.plan_id)).scalars().all()
        return [_load_version(connection, version_id) for version_id in ids]
