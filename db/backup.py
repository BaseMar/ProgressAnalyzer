"""Back up a database or restore into a new SQLite file / empty PostgreSQL public schema."""

import argparse
import os
import shutil
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


class BackupError(ValueError):
    """A backup operation failed without exposing database credentials."""


def _url(value):
    url = make_url(value)
    if url.get_backend_name() not in ("sqlite", "postgresql"):
        raise BackupError("Supported backends are SQLite and PostgreSQL")
    if url.query.keys() - {"sslmode", "sslrootcert", "sslcert", "sslkey", "connect_timeout"}:
        raise BackupError("Unsupported connection URL options for backup/restore")
    return url


def _sqlite_path(url):
    if not url.database or url.database == ":memory:":
        raise BackupError("Choose a file-backed SQLite database")
    return Path(url.database).resolve()


def _sqlite_read(path):
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def _check_sqlite(connection):
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise BackupError("SQLite integrity check failed")


def _postgres_command(tool, url, pg_bin=None):
    executable = Path(pg_bin) / tool if pg_bin else shutil.which(tool)
    if pg_bin and os.name == "nt":
        executable = executable.with_suffix(".exe")
    if not executable or not Path(executable).is_file():
        raise BackupError(f"{tool} is unavailable; add PostgreSQL tools to PATH or pass --pg-bin")
    # Credentials belong in the child's environment, never command arguments or output.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    environment.update(
        PGHOST=url.host or "localhost",
        PGPORT=str(url.port or 5432),
        PGDATABASE=url.database or "postgres",
        PGUSER=url.username or "postgres",
        PGPASSWORD=url.password or "",
        PGCONNECT_TIMEOUT="15",
    )
    for key, value in url.query.items():
        environment["PG" + key.upper()] = value
    return [str(executable), "--no-password"], environment


def _run(command, environment):
    try:
        subprocess.run(command, env=environment, check=True, capture_output=True)
    except (subprocess.CalledProcessError, OSError):
        raise BackupError(
            "PostgreSQL operation failed. Check connectivity, permissions and client/server versions; "
            "no credentials were printed."
        ) from None


def _copy_sqlite(source, target):
    with closing(_sqlite_read(source)) as original:
        _check_sqlite(original)
        with closing(sqlite3.connect(target)) as destination:
            original.backup(destination)
            _check_sqlite(destination)


def create_backup(url_value, output, *, pg_bin=None):
    """Publish a complete snapshot once; existing files are never overwritten."""
    url = _url(url_value)
    output = Path(output).resolve()
    if output.exists():
        raise BackupError("Backup file already exists; choose another filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".backup-", dir=output.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        if url.get_backend_name() == "sqlite":
            _copy_sqlite(_sqlite_path(url), temporary)
        else:
            command, environment = _postgres_command("pg_dump", url, pg_bin)
            _run(
                command
                + [
                    "--format=custom",
                    "--schema=public",
                    "--no-owner",
                    "--no-privileges",
                    "--file",
                    str(temporary),
                ],
                environment,
            )
            with temporary.open("rb") as archive:
                if archive.read(5) != b"PGDMP":
                    raise BackupError("PostgreSQL did not produce a custom-format archive")
        # Both files are on the same filesystem. Linking publishes without a replace race.
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def restore_backup(url_value, backup, *, pg_bin=None):
    """Restore trusted snapshots into a separate, empty target; never replace records."""
    url = _url(url_value)
    backup = Path(backup).resolve()
    if not backup.is_file():
        raise BackupError("Backup file does not exist")
    if url.get_backend_name() == "sqlite":
        target = _sqlite_path(url)
        if target.exists():
            raise BackupError("Restore requires a new SQLite filename; existing files are retained")
        return create_backup(f"sqlite:///{backup.as_posix()}", target)
    with backup.open("rb") as source:
        if source.read(5) != b"PGDMP":
            raise BackupError("PostgreSQL restore requires a custom-format archive")
    command, environment = _postgres_command("pg_restore", url, pg_bin)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            # Include sequences, views, routines and types, not just application tables.
            occupied = connection.execute(
                text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='public'
                    UNION ALL
                    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname='public'
                    UNION ALL
                    SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                    WHERE n.nspname='public'
                )
            """)
            ).scalar_one()
            if occupied:
                raise BackupError(
                    "Restore requires an empty public schema; existing objects are retained"
                )
        _run(
            command
            + [
                "--dbname",
                environment["PGDATABASE"],
                "--single-transaction",
                "--exit-on-error",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                str(backup),
            ],
            environment,
        )
    finally:
        engine.dispose()
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("create", "restore"))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--url", help="Explicit source/target SQLAlchemy URL")
    target.add_argument(
        "--url-env", help="Read the URL from this environment variable; no .env lookup"
    )
    parser.add_argument("--file", required=True, type=Path, help="Backup output or restore input")
    parser.add_argument("--pg-bin", type=Path, help="Directory containing pg_dump and pg_restore")
    args = parser.parse_args()
    url = args.url or os.getenv(args.url_env, "")
    if not url:
        parser.exit(2, "Database URL is missing.\n")
    try:
        operation = create_backup if args.operation == "create" else restore_backup
        operation(url, args.file, pg_bin=args.pg_bin)
    except BackupError as error:
        parser.exit(2, f"{error}\n")
    except (ValueError, OSError, sqlite3.Error):
        parser.exit(
            2, "Backup operation failed. Check the selected file, URL and target emptiness.\n"
        )
    except Exception:
        parser.exit(2, "Database operation failed. Connection details were not printed.\n")
    print(
        "Backup created."
        if args.operation == "create"
        else "Backup restored into the empty target."
    )


if __name__ == "__main__":
    main()
