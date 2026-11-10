# Backup and restore

`python -m db.backup` creates a consistent database snapshot and restores it
into a separate target. It does not load `.env` or Streamlit secrets. Select the
source or target explicitly with `--url`, or use `--url-env VARIABLE_NAME` to
keep PostgreSQL credentials out of the command itself.

## SQLite

From the repository root:

```sh
python -m db.backup create --url sqlite:///demo.sqlite3 --file backups/workouts.sqlite3
python -m db.backup restore --url sqlite:///restored.sqlite3 --file backups/workouts.sqlite3
```

Use a new backup filename each time. Existing backup files and restore targets
are refused. The implementation uses SQLite's
[online backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup),
which includes committed writes in WAL mode, and checks database integrity.
Snapshots are published only after completion; a failed operation leaves no
partial output. The source is opened read-only.

Open the recovered copy explicitly to inspect it:

```powershell
$env:DATABASE_URL = "sqlite:///restored.sqlite3"
streamlit run personal_app.py
```

## PostgreSQL

Install PostgreSQL client tools matching the server's major version. Both
`pg_dump` and `pg_restore` must be on `PATH`, or specify their directory with
`--pg-bin`. There is no hard-coded installation path or Windows-only dependency.

With `DATABASE_URL` already set to the source and `RESTORE_DATABASE_URL` set to
a separate, empty target:

```sh
python -m db.backup create --url-env DATABASE_URL --file backups/workouts.dump
python -m db.backup restore --url-env RESTORE_DATABASE_URL --file backups/workouts.dump
```

PowerShell example when the tools are outside `PATH`:

```powershell
python -m db.backup create --url-env DATABASE_URL --file backups/workouts.dump --pg-bin "C:\Program Files\PostgreSQL\16\bin"
```

The archive covers the application's **public schema**, including tables,
constraints, indexes and sequences. It excludes Supabase-managed authentication,
storage and other schemas, roles, ownership and grants. This is an application
data recovery tool, not a backup of an entire hosted service.

The tool uses the PostgreSQL
[custom archive format](https://www.postgresql.org/docs/16/app-pgdump.html) and
[transactional restore](https://www.postgresql.org/docs/16/app-pgrestore.html).
Restore checks that `public` contains no relations, routines or types and refuses
an occupied schema. Stop the target app while restoring so another writer cannot
populate it between the check and restore. Ownership/privileges are not restored;
the restore role owns the recovered objects. Supply only trusted backups.

The CLI reports failures without printing subprocess stderr or connection
credentials. Existing SQL dumps from the old local `backup_db.py` are retained;
this command accepts native custom archives, not those older plain SQL files.

## Recovery check and routine

Keep personal backups outside Git, periodically copy them to another device
or storage location, and create one before a schema upgrade. `backups/` is
ignored by Git and excluded from Docker images. The old ignored local helper
is not part of the maintained tool and can be retired after verifying a new copy.

For a recovery rehearsal, restore into an empty test database, compare table
contents, open all four application pages and record a test workout there.
Do not point the rehearsal at the active personal database.

Automated SQLite and PostgreSQL tests compare every application's table before
and after recovery, verify that the source stayed unchanged and confirm a write
works after restore. PostgreSQL acceptance checks sequence continuity and the
refusal to restore into an occupied source database.
