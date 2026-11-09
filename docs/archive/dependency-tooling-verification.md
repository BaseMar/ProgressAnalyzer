# Dependency and tooling verification: stage 7

> Historical record: verified against application commit `664b817` on 9 November
> 2026. For current commands, see [development tools](../development-tools.md).

A fresh Python 3.12 environment installed only `requirements.txt` first. The
complete synthetic dashboard benchmark ran before pytest or Ruff was installed.
Neither psycopg 3 nor pyodbc was present. The plain PostgreSQL URL selected the
psycopg2 dialect, and `pip check` passed. Development tools were then installed
through `requirements-dev.txt` for the full checks.

The historical [stage 7 artifact](../baselines/stage-7.json) records test counts, render samples,
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

GitHub Actions completed with **572 passed** on each of Python 3.11 and 3.12,
including all PostgreSQL cases: [stage 7 CI run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/42634368546).
Documentation consolidation and final acceptance follow this stage.

The stage 7 formatting pass also sorted imports and removed unused imports.
Small lint corrections removed an unused exception binding, replaced a local
assigned lambda with a function, removed an unnecessary f-string prefix and
expressed boolean checks without `== True/False`. No recommendation formula or
history-selection policy changed. Source-line totals increased with the shared
format rather than new application features.
