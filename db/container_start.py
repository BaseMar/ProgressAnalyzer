"""Prepare the container's demo database, then replace this process with Streamlit."""

import os
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

from db.bootstrap import ConnectionScope, bootstrap_database, initialization_transaction
from db.migrate import ledger, migrate
from db.schema import define_base_tables


def ensure_database(engine):
    """Seed an empty target once; migrate a recognized installation without reseeding."""
    with initialization_transaction(engine) as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        scope = ConnectionScope(connection)
        if not tables and not inspector.get_view_names():
            result = bootstrap_database(scope, demo=True)
            return {"created": True, "migrations": result["migrations"]}
        required = set(define_base_tables().tables) | {ledger.name}
        if not required <= tables:
            raise ValueError(
                "Container database has an unrecognized or incomplete schema; no demo data was added"
            )
        revisions = migrate(scope, apply=True)
        return {"created": False, "migrations": revisions}


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("Set DATABASE_URL for the container database")
    if len(sys.argv) < 2:
        raise SystemExit("Pass the application command after the container entrypoint")
    engine = None
    try:
        engine = create_engine(url)
        result = ensure_database(engine)
    except (ValueError, RuntimeError, SQLAlchemyError):
        raise SystemExit(
            "Container database initialization failed; check database availability, permissions and migration compatibility"
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
    print(
        "Created a new synthetic demo database."
        if result["created"]
        else "Existing database retained; demo data was not regenerated.",
        flush=True,
    )
    print(f"Applied {len(result['migrations'])} migrations.", flush=True)
    # Streamlit becomes PID 1 so Docker stop/restart signals reach it directly.
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
