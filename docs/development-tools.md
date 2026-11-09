# Development dependencies and checks

Stage 7 separates application dependencies from development tools and gives
local development, the dev container and GitHub Actions the same Python checks.
Documentation and implementation comments remain in English.

## Dependency ownership

| Manifest | Purpose | Direct dependencies |
| --- | --- | --- |
| `requirements.txt` | Run the dashboard and administrative/benchmark commands | Streamlit, pandas, NumPy, Plotly, Pillow, SQLAlchemy, python-dotenv, psycopg2-binary |
| `requirements-dev.txt` | Test, lint and format the project; includes the runtime manifest | pytest, Ruff |

Every direct dependency has an exact version. Runtime versions match those
used for the stage 6 regression baseline. pytest is a development dependency;
the dashboard does not need it to run. Ruff supplies both linting and formatting,
so separate Black, Flake8 and isort installations are unnecessary.

The unused `psycopg[binary]` and `pyodbc` declarations are removed. PostgreSQL
uses `psycopg2-binary`: both `postgresql+psycopg2://` and the existing plain
`postgresql://` URLs resolve to that driver under the pinned SQLAlchemy 2.0
version. This follows the [SQLAlchemy PostgreSQL dialect documentation](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#dialect-postgresql-psycopg2).
No database URL, stored workout or schema migration is changed.

These are direct dependency pins, not a complete transitive lock. pip still
resolves their dependency ranges for the current platform and Python version.
The [stage 7 artifact](baselines/stage-7.json) records the resolved packages from
the fresh local runtime installation, alongside regression evidence. That
package list describes the measurement environment; it is not another install
manifest. Broad package upgrades are outside this stage.

## One Python style

Ruff is pinned to `0.17.4` in the development manifest and required by
`pyproject.toml`. Its [configuration](https://docs.astral.sh/ruff/configuration/)
and [formatter](https://docs.astral.sh/ruff/formatter/) share that file:

- Python 3.11 syntax target, compatible with both supported CI versions.
- A 100-character formatting target, double quotes, spaces and LF line endings.
- `E4`, `E7`, `E9` and `F` checks for structural errors, undefined/unused names
  and related correctness issues, plus `I` for import sorting.
- Generated caches, backups and saved local settings excluded from discovery.

The line length is a formatter target, not a guarantee that string literals or
comments fit within 100 characters. No broad complexity, typing or docstring
rule set is introduced as part of this formatting pass.

Shared pytest fixtures imported from another test module use explicit
`name as name` re-exports. The same convention preserves existing public
exports in `db.plan_adherence` and `ui.utils.set_load_inputs`. Tests and export
modules do not have blanket unused-import exclusions. The only per-file rule
exception is `E402` in `scripts/benchmark_project.py`, whose executable entry
point sets the repository import path before importing application modules.

All tracked Python files use the shared format. Safe lint fixes sort imports
and remove unused imports; a few small lint corrections remove an unused
exception binding, replace a local assigned lambda with a function, remove an
unnecessary f-string prefix and express boolean checks without `== True/False`.
This stage changes no recommendation formula or history-selection policy.
Formatted source occupies more lines than the compact stage 6 style; that
increase does not represent new application features.

`.gitattributes` keeps Python, TOML, workflow and requirements files on LF across
checkouts. `.ruff_cache/` is ignored. The existing `pytest.ini` continues to own
pytest settings.

## Local and CI workflow

From an activated Python 3.11 or 3.12 virtual environment:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m compileall -q db metrics models services ui scripts streamlit_app.py data_loader.py data_manager.py mapper.py
```

To apply formatting and safe lint fixes:

```powershell
python -m ruff check --fix .
python -m ruff format .
```

Review fixes before committing. A clean `ruff check` and `ruff format --check`
must pass afterward.

The [Tests workflow](../.github/workflows/tests.yml) runs these checks on Python
3.11 and 3.12. Each matrix job receives its own disposable PostgreSQL 16 service
and executes the six database integration cases, in addition to the regular
unit, SQLite and Streamlit tests. Local runs skip those six cases unless
`TEST_POSTGRES_URL` is configured; they never use the application's database URL
as a test-database fallback. pip caching keys include both dependency manifests.

The [dev container](../.devcontainer/devcontainer.json) uses the official
[Python 3.12 Bookworm image](https://github.com/devcontainers/images/tree/main/src/python),
installs `requirements-dev.txt` once and configures the official
[Ruff editor extension](https://docs.astral.sh/ruff/editors/setup/) to use the
environment's pinned tool. Format-on-save and explicit save actions use the
same rules as CI. The configuration is parsed locally; starting the container
itself is not part of the local verification evidence.

## Dependency changes

1. Edit the owning manifest. Keep application dependencies in the runtime file
   and development-only tools in the development file.
2. Install into a fresh environment, then run `pip check` and all CI checks.
3. If changing Ruff, update its required version in `pyproject.toml` with the
   development pin and review the resulting lint/format changes together.
4. For application dependency changes, compare the synthetic semantic fixture
   and rendered routes using `scripts/benchmark_project.py`. Optional live
   measurements must retain the runner's read-only and integrity guards.

## Verification evidence

A fresh Python 3.12 environment installed only `requirements.txt` first. The
complete synthetic dashboard benchmark ran before pytest or Ruff was installed.
Neither psycopg 3 nor pyodbc was present. The plain PostgreSQL URL selected the
psycopg2 dialect, and `pip check` passed. Development tools were then installed
through `requirements-dev.txt` for the full checks.

The [stage 7 artifact](baselines/stage-7.json) records test counts, render samples,
SQL counts and comparisons with stage 6. The frozen semantic fixture remains
unchanged. The live benchmark reads the existing dataset without applying
migrations, seeding records or changing historical load interpretation.

Local verification reports **566 passed, 6 skipped**, with no test failures.
All **159 tracked Python files** pass linting, formatting and Python 3.11 syntax
parsing; compilation and dependency consistency checks also pass. The seven
semantic sections, nine captured route outputs on each dataset and twenty warm
SQL-count comparisons match stage 6. Both database-integrity checks pass,
including preservation of all **2531 existing recorded sets** in PostgreSQL.
Timing samples are retained for comparison, without claiming a performance
gain from formatting or dependency separation.

This stage establishes dependency and code-quality checks. Consolidating the
remaining documentation and final acceptance remain stages 8 and 9.
