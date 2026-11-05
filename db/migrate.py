"""Explicit migrations: python -m db.migrate [--apply]. Default is read-only."""

import argparse

from sqlalchemy import Column, DateTime, MetaData, String, Table, func, inspect, select, text

from db.migrations import v001_training_plans, v002_plan_session_links, v003_exercise_matches, v004_set_classifications, v005_progression_settings, v006_set_loads

MIGRATIONS = (v001_training_plans, v002_plan_session_links, v003_exercise_matches, v004_set_classifications, v005_progression_settings, v006_set_loads)
metadata = MetaData()
ledger = Table("schema_migrations", metadata,
    Column("revision", String(100), primary_key=True),
    Column("applied_at", DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()),
)


def pending_migrations(connection) -> list:
    applied = set()
    if inspect(connection).has_table(ledger.name):
        applied = set(connection.execute(select(ledger.c.revision)).scalars())
    unknown = applied - {migration.REVISION for migration in MIGRATIONS}
    if unknown:
        raise RuntimeError("Database contains migrations unknown to this application")
    return [migration for migration in MIGRATIONS if migration.REVISION not in applied]


def migrate(engine, *, apply: bool = False) -> list[str]:
    with engine.begin() as connection:
        if not apply:
            return [migration.REVISION for migration in pending_migrations(connection)]
        if connection.dialect.name == "postgresql":
            # Serializes migration runners within this transaction.
            connection.execute(text("SELECT pg_advisory_xact_lock(917420001)"))
        ledger.create(connection, checkfirst=True)
        pending = pending_migrations(connection)
        for migration in pending:
            migration.apply(connection)
            connection.execute(ledger.insert().values(revision=migration.REVISION))
        return [migration.REVISION for migration in pending]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply pending migrations")
    args = parser.parse_args()
    from db.connection import get_engine
    revisions = migrate(get_engine(), apply=args.apply)
    print(("Applied: " if args.apply else "Pending: ") + (", ".join(revisions) or "none"))


if __name__ == "__main__":
    main()
