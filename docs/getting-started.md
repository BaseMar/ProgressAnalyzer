# Local setup and database migrations

After cloning, run Python commands from the repository root. The activation
example uses Windows PowerShell; Python module commands are the same on other platforms.
The public demo has one shared dataset; there is no authentication or user-data
isolation. See [architecture](architecture.md#data-model) for storage ownership.

## Requirements

- Python 3.11 or 3.12, both tested in CI.
- An existing PostgreSQL-compatible database with the expected workout and
  body-tracking tables.
- Dependencies listed in `requirements.txt`.

The repository includes additive migrations, **not a complete bootstrap of the
original schema or a sample dataset**. Cloning the repository alone does not
create a ready-to-use database. For a quick look, use the [live demo](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).

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

Create `.env` in the project root and supply your database connection.
The file is ignored by Git. Use the credentials for the database you intend to run.

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

Preview and apply the additive migrations, then start the app:

```powershell
python -m db.migrate
python -m db.migrate --apply
streamlit run streamlit_app.py
```

Direct runtime dependencies, including Streamlit, are pinned in `requirements.txt`
so local installs and Community Cloud use the same renderer.
Reinstall requirements after dependency changes. Development tools are installed
separately through `requirements-dev.txt`, which includes the runtime manifest.
A missing connection or missing base tables prevents startup data loading.

The connection reader checks the environment (including local `.env`) first,
then the `DATABASE_URL` key in Streamlit secrets. Both
`postgresql+psycopg2://` and plain `postgresql://` use the supported psycopg2
driver with the pinned SQLAlchemy version.

For tests, linting and the dev container, follow the
[development tools guide](development-tools.md). Its development manifest
includes all runtime dependencies; a second runtime install is unnecessary.

## Database migrations

A migration adds a versioned database change. They run only when explicitly
requested, never during app startup.

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

The migrations require the original catalog/workout tables, including
`exercises`, `workout_sessions`, `workout_exercises` and `workout_sets`.
They preserve historical workout values; migration 006 does not reinterpret
legacy weights. Existing plans do not receive an assumed block configuration.

PostgreSQL runs each application of pending revisions in a transaction with
a migration lock. Completed revisions are skipped on later runs. An untracked
conflicting table causes an error.

Body-mass suggestions support legacy text dates and date/timestamp columns;
invalid or future measurements are skipped without changing them.
Source data may be cached for up to five minutes; imports and corrections
invalidate the cache.

To seed exercise–muscle mappings in a configured database:

```powershell
python -m db.seed_exercise_muscle_map
```

</details>

## Synthetic verification without an application database

After installing the development dependencies, `python -m pytest` runs the
unit, SQLite and Streamlit checks without `DATABASE_URL`. Six PostgreSQL cases
need the separate `TEST_POSTGRES_URL` described in the
[development tools guide](development-tools.md#local-and-ci-workflow).

The synthetic benchmark creates its own temporary SQLite fixture:

```powershell
python scripts/benchmark_project.py --output .cache/baseline/current.json
```

This fixture is for tests and measurements; it does not bootstrap a deployable
PostgreSQL database. The optional `--live` benchmark reads the configured
application database under read-only and integrity guards. See the
[measurement method](archive/performance-baseline.md#measurement-method) before
comparing results with historical captures.
