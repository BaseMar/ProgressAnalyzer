"""Resolve versioned weekly schedules and explicitly link recorded sessions."""

from datetime import date, datetime, timedelta

from sqlalchemy import Column, Date, Integer, MetaData, Table, Time, select
from sqlalchemy.exc import IntegrityError

from db.migrations.v002_plan_session_links import define_table
from db.read_cache import has_table, read_cached
from db.training_plans import _load_version, days, plans, versions
from models.scheduled_workout import ScheduledWorkout

metadata = MetaData()
Table("training_plan_days", metadata, Column("day_id", Integer, primary_key=True))
sessions = Table(
    "workout_sessions",
    metadata,
    Column("session_id", Integer, primary_key=True),
    Column("session_date", Date),
    Column("start_time", Time),
)
links = define_table(metadata)


def plan_schedule_storage_ready(engine):
    with engine.connect() as connection:
        return has_table(connection, links.name)


@read_cached
def _schedule_rows(engine, plan_id):
    """Read plan schedule inputs once for all date windows in a render."""
    with engine.connect() as connection:
        version_rows = (
            connection.execute(
                select(versions)
                .where(
                    versions.c.plan_id == plan_id,
                )
                .order_by(versions.c.effective_from)
            )
            .mappings()
            .all()
        )
        day_rows = (
            connection.execute(
                select(days)
                .join(versions)
                .where(
                    versions.c.plan_id == plan_id,
                )
                .order_by(days.c.position)
            )
            .mappings()
            .all()
        )
        assigned = (
            connection.execute(
                select(links, sessions.c.session_date)
                .join(sessions)
                .join(days, links.c.day_id == days.c.day_id)
                .join(versions, days.c.version_id == versions.c.version_id)
                .where(versions.c.plan_id == plan_id)
            )
            .mappings()
            .all()
        )
    return version_rows, day_rows, assigned


@read_cached
def load_scheduled_workouts(engine, plan_id: int, start: date, end: date) -> list[ScheduledWorkout]:
    if start > end:
        raise ValueError("Schedule start must not exceed end")
    version_rows, day_rows, assigned = _schedule_rows(engine, plan_id)
    by_slot = {(row["day_id"], row["scheduled_date"]): row for row in assigned}
    result = []
    for index, version in enumerate(version_rows):
        first = max(start, version["effective_from"])
        last = end
        if index + 1 < len(version_rows):
            last = min(last, version_rows[index + 1]["effective_from"] - timedelta(days=1))
        if first > last:
            continue
        for day in day_rows:
            if day["version_id"] != version["version_id"]:
                continue
            current = first + timedelta(days=(day["weekday"] - first.weekday()) % 7)
            while current <= last:
                assignment = by_slot.get((day["day_id"], current))
                result.append(
                    ScheduledWorkout(
                        day_id=day["day_id"],
                        version_id=version["version_id"],
                        scheduled_date=current,
                        name=day["name"],
                        session_id=assignment["session_id"] if assignment else None,
                        performed_on=(
                            assignment["session_date"].date()
                            if isinstance(assignment["session_date"], datetime)
                            else assignment["session_date"]
                        )
                        if assignment
                        else None,
                        position=day["position"],
                    )
                )
                current += timedelta(days=7)
    return sorted(result, key=lambda item: item.scheduled_date)


@read_cached
def load_scheduled_workout_targets(engine, day_id: int):
    with engine.connect() as connection:
        row = (
            connection.execute(select(days).where(days.c.day_id == day_id)).mappings().one_or_none()
        )
        if row is None:
            raise ValueError("Planned workout not found")
        version = _load_version(connection, row["version_id"])
        return version.draft.days[row["position"] - 1]


@read_cached
def load_plan_session_links(engine) -> dict[int, tuple[int, date]]:
    """Session identity -> scheduled slot, used to exclude already assigned logs."""
    with engine.connect() as connection:
        return {
            row.session_id: (row.day_id, row.scheduled_date)
            for row in connection.execute(select(links))
        }


def assign_scheduled_session(engine, day_id: int, scheduled_date: date, session_id: int):
    if type(scheduled_date) is not date:
        raise ValueError("A scheduled date is required")
    try:
        with engine.begin() as connection:
            day = (
                connection.execute(select(days).where(days.c.day_id == day_id))
                .mappings()
                .one_or_none()
            )
            if day is None:
                raise ValueError("Planned workout not found")
            plan_id = connection.execute(
                select(versions.c.plan_id).where(
                    versions.c.version_id == day["version_id"],
                )
            ).scalar_one()
            # Use the same plan lock as revision creation, so validation and
            # assignment cannot race a concurrent revision.
            connection.execute(
                select(plans.c.plan_id).where(plans.c.plan_id == plan_id).with_for_update()
            ).one()
            effective = connection.execute(
                select(versions.c.version_id)
                .where(
                    versions.c.plan_id == plan_id,
                    versions.c.effective_from <= scheduled_date,
                )
                .order_by(versions.c.effective_from.desc())
                .limit(1)
            ).scalar_one_or_none()
            if effective != day["version_id"] or scheduled_date.weekday() != day["weekday"]:
                raise ValueError("This workout is not scheduled on the selected date")
            if (
                connection.execute(
                    select(sessions.c.session_id).where(sessions.c.session_id == session_id)
                ).scalar_one_or_none()
                is None
            ):
                raise ValueError("Recorded session not found")
            existing = (
                connection.execute(select(links).where(links.c.session_id == session_id))
                .mappings()
                .one_or_none()
            )
            if (
                existing
                and existing["day_id"] == day_id
                and existing["scheduled_date"] == scheduled_date
            ):
                return
            connection.execute(
                links.insert().values(
                    session_id=session_id, day_id=day_id, scheduled_date=scheduled_date
                )
            )
    except IntegrityError as exc:
        raise ValueError(
            "This session or planned workout is already linked. Remove its existing link first."
        ) from exc


def unassign_scheduled_session(engine, day_id: int, scheduled_date: date, session_id: int):
    with engine.begin() as connection:
        connection.execute(
            links.delete().where(
                links.c.day_id == day_id,
                links.c.scheduled_date == scheduled_date,
                links.c.session_id == session_id,
            )
        )
