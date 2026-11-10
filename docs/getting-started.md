# Local setup, demo data and database migrations

After cloning, run Python commands from the repository root. The activation
example uses Windows PowerShell; Python module commands are the same on other platforms.
The public demo has one shared dataset; there is no authentication or user-data
isolation. See [architecture](architecture.md#data-model) for storage ownership.

For a containerized app and PostgreSQL with automatic first-start demo setup,
follow the [Docker Compose guide](docker.md). The instructions below cover
running Python directly on your host.

## Requirements

- Python 3.11 or 3.12, both tested in CI.
- SQLite, included with standard Python installations, for the local demo.
- A running PostgreSQL server and an empty database for the PostgreSQL alternative.
- Dependencies listed in `requirements.txt`.

The initializer creates the base tables, applies all additive migrations and
optionally generates fictional workout and measurement records. It uses the
same schema and application readers as a normal installation. For a hosted
preview, use the [live demo](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).

## Set up locally

Start in the folder where you want to clone the project. These activation
commands are for Windows PowerShell:

```powershell
git clone https://github.com/BaseMar/ProgressAnalyzer.git
cd ProgressAnalyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS, activate with `source .venv/bin/activate` instead.

## Run the local demo

These PowerShell commands create a new local file and select it for the app:

```powershell
python -m db.bootstrap --url sqlite:///demo.sqlite3 --demo
$env:DATABASE_URL = "sqlite:///demo.sqlite3"
streamlit run streamlit_app.py
```

For Bash, use `export DATABASE_URL=sqlite:///demo.sqlite3` before starting
Streamlit. No PostgreSQL server, account or Docker installation is needed.

The demo contains nine catalog exercises with muscle mappings, a three-day
weekly plan, about eight weeks of linked workouts and weekly body measurements.
It includes mixed loads, explicit bodyweight/assistance, timed sets, warm-ups,
missing RIR, a moved workout, an approved replacement and unlinked practice.
Dates are relative to today, keeping the history useful for the upcoming-workout
preview. Every value is generated from constants; the initializer does not read
personal training data, backups, the network or the existing application URL.
These fictional values illustrate software behavior rather than prescribe a routine.

Initialize a file **once**. If the target already contains tables or views,
bootstrap exits without changing records. To reopen the demo, run only the
environment selection and Streamlit command. Choose another filename for a
fresh dataset. Omit `--demo` for an empty application schema, or use
`--as-of YYYY-MM-DD` for a reproducible demonstration date.

The URL is required explicitly; bootstrap does not load `.env` or Streamlit
secrets. SQLite schema creation and demo seeding share one transaction, including
rollback of tables if initialization fails. SQLite must support `RETURNING`
(version 3.35 or newer, included in the tested Python installations).

To persist the app connection between terminal sessions, copy
[.env.example](../.env.example) to `.env` in a fresh clone, or set `DATABASE_URL`
in your existing local configuration. `.env` and generated `.sqlite3` files are
ignored by Git. A shell environment variable takes priority over the local file.

## PostgreSQL alternative

Create an empty database on an installed PostgreSQL server, for example with
your PostgreSQL administration tool or `CREATE DATABASE progress_analyzer_demo;`.
The initializer creates the application schema inside that database; server
installation and database-role provisioning are separate from this command.

```powershell
python -m db.bootstrap --url "postgresql+psycopg2://user:password@localhost:5432/progress_analyzer_demo" --demo
$env:DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/progress_analyzer_demo"
streamlit run streamlit_app.py
```

PostgreSQL initialization is transactional and uses the migration lock. The
target schema must be empty. Existing installations keep their tables and
recorded values; use the migration runner to upgrade them:

```powershell
python -m db.migrate
python -m db.migrate --apply
```

Direct runtime dependencies, including Streamlit, are pinned in `requirements.txt`
so local installs and Community Cloud use the same renderer.
Reinstall requirements after dependency changes. Development tools are installed
separately through `requirements-dev.txt`, which includes the runtime manifest.
A missing connection or an uninitialized database prevents startup data loading.

The connection reader checks the environment (including local `.env`) first,
then the `DATABASE_URL` key in Streamlit secrets. Both
`postgresql+psycopg2://` and plain `postgresql://` use the supported psycopg2
driver with the pinned SQLAlchemy version.

For tests, linting and the dev container, follow the
[development tools guide](development-tools.md). Its development manifest
includes all runtime dependencies; a second runtime install is unnecessary.

## Database migrations

A migration adds a versioned database change. Standalone Streamlit startup does
not run migrations. The Docker launcher prepares its dedicated demo database
before starting Streamlit; direct installations use the explicit commands below.

| Revision | Adds |
| --- | --- |
| 001 | Training plans and dated snapshots. |
| 002 | Links between recorded sessions and planned workouts. |
| 003 | Confirmed exercise replacements. |
| 004 | Optional set-purpose corrections. |
| 005 | Versioned progression/block settings. |
| 006 | Explicit set loads and body-mass snapshots. |
| 007 | Stable plan-position identities across revisions, without changing recorded workouts. |
| 008 | Saved manual starting loads per exercise and prescription, separate from recorded training history. |
| 009 | User-confirmed meanings of legacy bodyweight history, scoped to the exact exercise. |

`python -m db.migrate` previews pending revisions without writing.
`python -m db.migrate --apply` applies them and records successful revisions.

<details>
<summary>Migration and data-handling details</summary>

For fresh databases, `db.bootstrap` creates the catalog/workout/body tables
before applying these migrations. For existing databases, the migration runner
uses their original base tables.
They preserve historical workout values; migration 006 does not reinterpret
legacy weights. Existing plans do not receive an assumed block configuration.

PostgreSQL runs each application of pending revisions in a transaction with
a migration lock. Completed revisions are skipped on later runs. An untracked
conflicting table causes an error.

Body-mass suggestions support legacy text dates and date/timestamp columns;
invalid or future measurements are skipped without changing them.
Source data may be cached for up to five minutes; imports and corrections
invalidate the cache.

The demo already includes muscle mappings. The following administrative command
is for an existing PostgreSQL catalog containing its predefined exercises:

```powershell
python -m db.seed_exercise_muscle_map
```

</details>

## Synthetic verification without an application database

After installing the development dependencies, `python -m pytest` runs the
unit, SQLite and Streamlit checks without `DATABASE_URL`. PostgreSQL cases
need the separate `TEST_POSTGRES_URL` described in the
[development tools guide](development-tools.md#local-and-ci-workflow).

The synthetic benchmark creates its own temporary SQLite fixture:

```powershell
python scripts/benchmark_project.py --output .cache/baseline/current.json
```

This frozen fixture is separate from the deployable demo generated by
`db.bootstrap`; its reference dates and values remain unchanged. The optional
`--live` benchmark reads the configured
application database under read-only and integrity guards. See the
[measurement method](archive/performance-baseline.md#measurement-method) before
comparing results with historical captures.
