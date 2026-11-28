"""Read live assignments or the historical context retained when they are removed."""

from datetime import date, datetime

from sqlalchemy import Column, Integer, MetaData, String, Table, and_, cast, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.migrations.v012_session_provenance import define_table
from db.read_cache import has_table, read_cached
from metrics.training_block import is_deload_workout, training_block_phase
from models.scheduled_workout import ScheduledWorkout
from models.training_plan import ProgressionSettings

metadata = MetaData()
Table("workout_sessions", metadata, Column("session_id", Integer, primary_key=True))
provenance = define_table(metadata)
TARGET_FIELDS = (
    "plan_exercise_id",
    "exercise_id",
    "position",
    "set_count",
    "target_min",
    "target_max",
    "target_unit",
    "target_rir",
    "history_key",
    "workout_exercise_id",
)


def recorded_date(value):
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(value[:10]) if isinstance(value, str) else value


def source_phase(scheduled, performed, block_start, block_weeks):
    if block_start is None:
        return "unknown"
    scheduled, performed = recorded_date(scheduled), recorded_date(performed)
    settings = ProgressionSettings(recorded_date(block_start), block_weeks)
    slot = ScheduledWorkout(0, 0, scheduled, "", performed_on=performed)
    if is_deload_workout(slot, settings):
        return "deload"
    if performed is not None and training_block_phase(performed, settings).phase == "normal":
        return "normal"
    return "unknown"


def linked_session_provenance(connection, session_ids=None):
    """Build source metadata from assigned versions and explicit exercise matches."""
    from db.plan_adherence import matches
    from db.plan_schedule import links, sessions
    from db.training_plans import days, exercise_lineage, plans, progression_settings, versions
    from db.training_plans import exercises as targets

    query = (
        select(
            links.c.session_id,
            versions.c.plan_id,
            plans.c.created_at.label("plan_created_at"),
            days.c.version_id,
            links.c.day_id,
            links.c.scheduled_date,
            days.c.name.label("workout"),
            days.c.position.label("workout_position"),
            cast(sessions.c.session_date, String).label("session_date"),
            progression_settings.c.block_start,
            progression_settings.c.block_weeks,
            targets,
            exercise_lineage.c.history_key,
            matches.c.workout_exercise_id,
        )
        .select_from(
            links.join(sessions)
            .join(days, days.c.day_id == links.c.day_id)
            .join(versions)
            .join(plans)
        )
        .outerjoin(progression_settings, progression_settings.c.version_id == days.c.version_id)
        .join(targets, targets.c.day_id == days.c.day_id)
        .outerjoin(
            exercise_lineage, exercise_lineage.c.plan_exercise_id == targets.c.plan_exercise_id
        )
        .outerjoin(
            matches,
            and_(
                matches.c.session_id == links.c.session_id,
                matches.c.plan_exercise_id == targets.c.plan_exercise_id,
            ),
        )
        .order_by(links.c.session_id, targets.c.position)
    )
    if session_ids is not None:
        query = query.where(links.c.session_id.in_(session_ids))
    output = {}
    for row in connection.execute(query).mappings():
        session_id = row["session_id"]
        if session_id not in output:
            output[session_id] = {
                **{
                    key: row[key]
                    for key in (
                        "session_id",
                        "plan_id",
                        "plan_created_at",
                        "version_id",
                        "day_id",
                        "scheduled_date",
                        "workout",
                        "workout_position",
                    )
                },
                "phase": source_phase(
                    row["scheduled_date"],
                    row["session_date"],
                    row["block_start"],
                    row["block_weeks"],
                ),
                "targets": [],
            }
        output[session_id]["targets"].append({key: row[key] for key in TARGET_FIELDS})
    return output


def preserve_session_provenance(connection, session_ids=None, *, required=False):
    """Snapshot only known assignments, in the transaction that changes their links."""
    if not has_table(connection, provenance.name):
        if required:
            raise ValueError("Apply the session provenance migration before removing plan links.")
        return
    sources = linked_session_provenance(connection, session_ids)
    if sources:
        insert = pg_insert if connection.dialect.name == "postgresql" else sqlite_insert
        statement = insert(provenance)
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=[provenance.c.session_id],
                set_={
                    column.name: statement.excluded[column.name]
                    for column in provenance.c
                    if column.name != "session_id"
                },
            ),
            list(sources.values()),
        )


def detached_session_provenance(connection, session_ids, *, plan_id=None, cutoff=None):
    from db.plan_schedule import links, sessions
    from db.training_plans import plans

    if (not session_ids and plan_id is None) or not has_table(connection, provenance.name):
        return {}
    query = select(provenance).where(
        ~select(links.c.session_id).where(links.c.session_id == provenance.c.session_id).exists()
    )
    requested = provenance.c.session_id.in_(session_ids)
    if plan_id is not None:
        current_created_at = (
            select(plans.c.created_at).where(plans.c.plan_id == plan_id).scalar_subquery()
        )
        requested = or_(requested, provenance.c.plan_id == plan_id)
        query = query.add_columns(
            cast(sessions.c.session_date, String).label("session_date"),
            sessions.c.start_time,
            current_created_at.label("current_plan_created_at"),
        ).join(sessions, sessions.c.session_id == provenance.c.session_id)
        query = query.where(sessions.c.session_date < cutoff)
    query = query.where(requested)
    rows = connection.execute(query).mappings()
    if plan_id is None:
        return {row["session_id"]: row for row in rows}
    # Compare decoded timestamps so SQLite legacy defaults with no fractional seconds match.
    return {
        row["session_id"]: {
            **row,
            "source_plan_matches": row["plan_id"] == plan_id
            and row["plan_created_at"] == row["current_plan_created_at"],
        }
        for row in rows
    }


@read_cached
def load_retained_session_context(engine, session_id):
    with engine.connect() as connection:
        return detached_session_provenance(connection, (session_id,)).get(session_id)


def clear_retained_session_context(engine, session_id):
    """Explicitly correct an unlinked session whose old assignment was wrong."""
    from db.plan_schedule import links, sessions

    with engine.begin() as connection:
        if not has_table(connection, provenance.name):
            return False
        locked = connection.execute(
            select(sessions.c.session_id)
            .where(sessions.c.session_id == session_id)
            .with_for_update()
        ).scalar_one_or_none()
        if locked is None:
            return False
        if connection.execute(
            select(links.c.session_id).where(links.c.session_id == session_id)
        ).first():
            raise ValueError(
                "Relink this session or remove its calendar link before clearing context."
            )
        return (
            connection.execute(
                provenance.delete().where(provenance.c.session_id == session_id)
            ).rowcount
            == 1
        )
