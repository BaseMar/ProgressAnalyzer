"""Initialize an empty SQLite/PostgreSQL schema, optionally with synthetic demo data."""

import argparse
from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError

from db.migrate import migrate
from db.schema import define_base_tables


class ConnectionScope:
    """Let existing writers share the bootstrap's single transaction."""

    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def bootstrap_database(engine, *, demo=False, as_of=None):
    """Create all tables once; reject existing schemas before changing records.

    A failed migration or seed rolls back the entire initialization. The target
    engine is explicit: this module never loads DATABASE_URL or app secrets.
    """
    as_of = date.today() if as_of is None else as_of
    if type(as_of) is not date:
        raise ValueError("The demo reference date must be a date")
    with engine.begin() as connection:
        dialect = connection.dialect.name
        if dialect not in ("sqlite", "postgresql"):
            raise ValueError("Bootstrap supports SQLite and PostgreSQL")
        if dialect == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            # Python's legacy SQLite transaction mode does not begin on DDL.
            if not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql("BEGIN")
        else:
            connection.execute(text("SELECT pg_advisory_xact_lock(917420001)"))
        inspector = inspect(connection)
        if inspector.get_table_names() or inspector.get_view_names():
            raise ValueError(
                "Target schema is not empty. Choose a new database/schema. "
                "Use python -m db.migrate --apply to upgrade an existing installation."
            )
        metadata = define_base_tables()
        metadata.create_all(connection, checkfirst=False)
        scope = ConnectionScope(connection)
        revisions = migrate(scope, apply=True)
        if demo:
            from db.demo_data import seed_demo

            seed_demo(scope, metadata.tables, as_of=as_of)
        counts = {
            name: connection.execute(select(func.count()).select_from(table)).scalar_one()
            for name, table in metadata.tables.items()
        }
    return {"migrations": revisions, "demo": demo, "counts": counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", required=True, help="Explicit target SQLAlchemy URL; the schema must be empty"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Include generated example workouts and measurements"
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Demo reference date (YYYY-MM-DD; default today)",
    )
    args = parser.parse_args()
    engine = None
    try:
        engine = create_engine(args.url)
        result = bootstrap_database(engine, demo=args.demo, as_of=args.as_of)
    except ValueError as error:
        parser.exit(2, f"Initialization failed: {error}\n")
    except SQLAlchemyError:
        parser.exit(
            2,
            "Initialization failed. Check the explicit target URL, database availability and permissions.\n",
        )
    finally:
        if engine is not None:
            engine.dispose()
    counts = result["counts"]
    print(f"Initialized schema; applied {len(result['migrations'])} migrations.")
    print(
        f"Exercises: {counts['exercises']}; sessions: {counts['workout_sessions']}; sets: {counts['workout_sets']}."
    )
    if args.demo:
        print("Demo data is entirely synthetic; no personal records or external sources were read.")


if __name__ == "__main__":
    main()
