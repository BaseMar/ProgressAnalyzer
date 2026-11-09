# Performance and regression baseline

Stage 3 of the project cleanup, measured on 9 November 2026. Application baseline:
`518ec80` (the stage 2 inventory commit). This stage adds measurement tooling and
reference tests; it does not optimize application code or change recommendation rules.

The machine-readable results, including individual warm samples, are in
[`baselines/stage-3.json`](baselines/stage-3.json). Reference calculation hashes
and reviewable examples are in
[`tests/fixtures/project_baseline.json`](../tests/fixtures/project_baseline.json).

## Environment and workloads

Windows AMD64, four logical CPUs; Python 3.12.2, Streamlit 1.66.1, SQLAlchemy 2.0.44,
Pandas 2.3.3, NumPy 2.3.5 and Plotly 6.5.0.

| Dataset | Sessions | Recorded exercise entries | Sets | Plan versions |
| --- | ---: | ---: | ---: | ---: |
| Synthetic, in-memory SQLite | 122 | 722 | 1950 | 2 |
| Existing application PostgreSQL | 127 | 884 | 2531 | 6 |

The synthetic workload spans 24 training weeks, five workouts per week and ten
catalog exercises. It includes warm-ups, mixed loads, timed holds, missing RIR,
legacy body-mass-only pull-ups, explicit assisted sets, a confirmed alternative,
unlinked history, a future entry and a plan revision changing RIR and set counts.
Body composition and circumference records are synthetic as well. The date is
fixed at 2026-11-09 for repeatable comparisons.

The two datasets have different plan/link histories. Their timings are separate
baselines rather than a database-engine comparison. No personal workout rows,
measurements, database URLs or credentials are included in the committed results.

## Measurement method

- The runner uses Streamlit `AppTest` against the actual `streamlit_app.py` entry
  point. It injects the selected engine into `DataManager`; application loading,
  existing cache decorators, routing and views remain in the execution path.
- Each route has one cache-cold render followed by three unchanged warm reruns.
  Cache-cold means a new AppTest session after clearing Streamlit data caches.
  Python imports and the database connection pool are already initialized; this
  is not a fresh-process or Cloud cold-start measurement.
- Analysis uses its default **All time** period. Both exercise scopes, plan
  consistency, both muscle-distribution views and body measurements are covered.
  Workout-switch samples alternate between the first two unlinked upcoming slots.
- SQLAlchemy cursor events count application SQL, including schema introspection.
  PostgreSQL read-only setup and SQLite `query_only` setup are excluded from SQL
  counts and SQL timers, but their round trips remain in elapsed wall time.
- SQL time covers cursor execution, not every fetch or connection-pool operation.
  Elapsed minus SQL time is therefore not a pure CPU measurement. Separate direct
  calculation timings use preloaded inputs and exclude SQL from their timers.
- Warm reruns must preserve displayed metrics, source tables, copied notes and
  recommendation cards. Database table fingerprints must match before and after.
- These are local server-side measurements, including serialization and test
  instrumentation. Browser paint, JavaScript interaction and frontend network
  transfer are outside the timer. Samples are a working comparison point, not an SLA.

Complete captures were followed by isolated Overview/workout-switch checks and
final All-time Analysis measurements. The tables and JSON use those final samples.
Only three warm samples are collected per case; SQL counts are also reported so
the optimization review does not depend on a single elapsed-time observation.

## Existing PostgreSQL results

Times are milliseconds. Warm time and warm SQL time are medians of three runs.
The cold column is one cache-cold sample. A dash means the interaction was
measured only after the page was ready.

| Route or interaction | Cold time | Warm time | Cold SQL count | Warm SQL count | Warm SQL time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overview | 11126.7 | 7922.5 | 140 | 128 | 5532.0 |
| Analysis: plan exercise progress | 7341.7 | 4167.1 | 82 | 70 | 2925.1 |
| Analysis: recorded exercises | 2571.8 | 86.6 | 12 | 0 | 0.0 |
| Analysis: plan consistency | 6595.3 | 4211.1 | 82 | 70-71 | 2949.3 |
| Analysis: muscle map | 4778.2 | 1154.7 | 27 | 15 | 620.6 |
| Analysis: set allocation | 3636.4 | 1157.9 | 27 | 15 | 619.1 |
| Analysis: body measurements | 2415.1 | 28.8 | 12 | 0 | 0.0 |
| Plan | 4817.3 | 2621.3 | 57 | 45 | 2117.4 |
| History | 10044.0 | 3806.8 | 73 | 61 | 2660.4 |
| Change upcoming workout | - | 7485.0 | - | 128 | 5234.3 |

The warm Overview samples each executed 128 statements. Repeated statement
shapes included 21 schema-existence lookups and 14 executions each of the version,
day, exercise-prescription and progression-setting queries. Parameters can differ;
these counts identify repeated access patterns, not proof that every query returns
identical rows.

The shared input cache avoids its twelve SQL statements on warm reruns. The
large remaining Overview/plan-analysis query counts therefore belong to the
per-render plan/recommendation services, not just the initial input loader.

## Synthetic SQLite results

| Route or interaction | Cold time | Warm time | Cold SQL count | Warm SQL count | Warm SQL time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overview | 1222.6 | 291.4 | 92 | 80 | 8.1 |
| Analysis: plan exercise progress | 1473.5 | 331.5 | 58 | 46 | 5.6 |
| Analysis: recorded exercises | 517.4 | 71.7 | 12 | 0 | 0.0 |
| Analysis: plan consistency | 703.1 | 180.6 | 58 | 46 | 5.7 |
| Analysis: muscle map | 1218.0 | 88.7 | 27 | 15 | 0.6 |
| Analysis: set allocation | 571.0 | 115.7 | 27 | 15 | 0.6 |
| Analysis: body measurements | 415.0 | 27.9 | 12 | 0 | 0.0 |
| Plan | 418.0 | 29.3 | 33 | 21 | 0.7 |
| History | 473.3 | 69.6 | 38 | 26 | 1.0 |
| Change upcoming workout | - | 288.1 | - | 80 | 7.6 |

The SQLite timings provide a repeatable workload without external database
latency. Overview still performs 80 warm SQL executions and repeated calculations.
The synthetic plan has substantially more linked historical sessions than the
existing application plan, which explains its larger plan-calculation workload.

## Calculation timings on preloaded inputs

Median milliseconds across three direct calls. Loading and test-fixture creation
are outside these timers. Individual calculation timings must not be added to
view timings: the views can call overlapping calculations more than once.

| Calculation | Synthetic workload | Existing workload |
| --- | ---: | ---: |
| Recorded exercise metrics | 33.877 | 56.664 |
| Plan adherence | 14.306 | 0.796 |
| Plan performance | 35.406 | 1.572 |
| Training insights | 38.846 | 2.376 |
| Weekly muscle allocation | 0.044 | 0.229 |
| Measurement timeline | 0.126 | 0.048 |

## Frozen behavior and test results

The reference hashes cover seven complete normalized output sections:
recommendations for the upcoming five workouts, ordinary/deload/return cases,
plan-adherence totals, plan-performance observations, recorded exercise metrics,
weekly muscle allocation and body-measurement timelines. Normalization sorts
dictionary keys, serializes dates, represents missing numeric values consistently
and rounds floating-point values to eight decimal places.

Selected results were reviewed before freezing the reference:

- The revised bench prescription reads 62.5 kg from newer ordinary unlinked
  history, retains target RIR 3 and does not increase weight. The future 200 kg
  entry does not become a recommendation.
- The row's changed set count produces four 70 kg starting sets.
- Confirmed body-mass-only pull-ups use 0 kg additional load; mixed curl loads
  remain 12/10/10 rather than becoming one average load.
- A recorded 35-second hold has a 40-second next target under ordinary progression.
- The isolated ordinary ceiling case increases 60 kg to 62.5 kg; deload retains
  10/10/10 reps at 40 kg; return resumes 60 kg without an immediate increase.

Ten new tests check the seven reference sections, reviewable examples, stability
when the wall clock moves forward, and write rejection/database preservation.
The full local suite reported **551 passed, 6 skipped**, with no failures, in
55.9 seconds. The six PostgreSQL integration cases were skipped because
`TEST_POSTGRES_URL` was not configured. Read-only production-query measurements
do not substitute for the separate PostgreSQL write/migration integration suite.
Existing tests continue to cover manual fallback, import compatibility and the
other progression/edge cases outside this workload.

## Database integrity

The runner rejects non-read-only SQL and enables database-level protection:
`SET TRANSACTION READ ONLY` for PostgreSQL or `PRAGMA query_only=ON` for SQLite.
The live check verified `transaction_read_only=on`. Tests also check SQLite's
driver-level write rejection independently of the SQL event guard.

Before/after hashes matched for every inspected application table in each completed
capture, including all 2531 recorded live sets, plans, links, classifications,
load snapshots and saved defaults. Fixture schema creation and seeding happen
only in a new in-memory database. Live mode does not apply migrations or seed data.

## Reproduce and compare after optimization

```powershell
# Portable render/calculation benchmark and full synthetic snapshot.
python scripts/benchmark_project.py --output .cache/baseline/current.json

# Focused query/latency check against the configured PostgreSQL database.
python scripts/benchmark_project.py --live --case overview --case workout_switch --output .cache/baseline/current-live.json

# Semantic references and write-protection checks.
python -m pytest tests/test_project_baseline.py

# Full regression suite; PostgreSQL cases require an explicit test URL.
python -m pytest
```

`--runs` controls warm sample count; `--case` can be repeated to select routes.
Default outputs and full raw SQL fingerprints stay under ignored `.cache/baseline/`.
Synthetic mode also exports `snapshot.json` next to the measurement output, so
a failing reference can be inspected without dumping personal application data.

Use the same fixture version, date, environment, period and sample definitions
when comparing later results. Preserve semantic references while changing caching
or query preparation. An intentional contract change needs a reviewed diff of
the full synthetic output; do not regenerate expected hashes just to pass tests.

## Priorities for stage 4

1. Load and share plan/version/history inputs within one render. Start with
   Overview and workout switching, where repeated SQL dominates the live cost.
2. Reuse table-availability information within a defined schema/cache lifetime;
   repeated inspection queries currently add many network round trips.
3. Remove redundant cache boundaries after inventorying invalidation. Preserve
   refresh after new logs, plan revisions, links, corrections and saved defaults.
4. Re-run the same route/case benchmarks and semantic reference tests. Keep
   starting-load history separate from strict progression evidence while
   consolidating readers and calculations.

The measurements establish the baseline. Speed improvements are to be measured
after the next stage rather than inferred from this report.
