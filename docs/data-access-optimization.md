# Data access and cache optimization

Stage 4 of the cleanup consolidates plan/history reads without changing the
recommendation rules. The comparison uses the workloads and measurement method
from the [stage 3 baseline](performance-baseline.md). Full samples are retained
in [`baselines/stage-4.json`](baselines/stage-4.json).

## Changes

- Plan snapshots load days, exercise prescriptions, progression settings and
  history keys in batches. Loading more versions increases the returned data,
  rather than adding another group of queries for every version.
- A read scope covers one execution of the Streamlit entry point. Plan versions,
  schedule inputs, linked records, confirmations and schema availability are
  shared within that render. Different date windows reuse their underlying
  schedule/history inputs while retaining their own calculated slots.
- The next-workout view uses the selected version's exercise prescriptions
  instead of loading the entire version again just to display one workout.
- Input loading has one five-minute Streamlit data cache. The former outer
  cache around `load_data()` has been removed, avoiding a second serialized copy
  and a second independent expiry boundary.
- Successful `DataManager` writes clear the input cache centrally. Views no
  longer clear every Streamlit data cache. Choosing an import-name mapping
  without writing to the database also no longer clears cached input data.
- Session deletion executes its three statements separately in the same
  transaction. This preserves atomic deletion and lets the SQLite regression
  workload exercise the same path as PostgreSQL.

There are no new runtime dependencies, schema migrations or persisted metric
results in this stage. Pure calculation modules retain their existing rules.

## Cache lifetime and invalidation

| Data | Lifetime | Refresh rule |
| --- | --- | --- |
| Database engine | Streamlit resource lifetime | Existing resource-cache behavior |
| Mapped workout/body input and joined sets | One `load_data()` cache, at most 300 seconds | Successful application writes clear this cache before returning |
| Plans, schedule inputs, linked history and confirmations | Current read scope only | Every render starts fresh; writes invalidate the active scope immediately |
| Schema availability | Current read scope only | Re-read on the next render; DDL invalidates the active scope |
| Heatmap assets/HTML | Existing argument-keyed cache | Unchanged; input changes select the corresponding cached result |

Input invalidation covers workout entry/import/deletion, plan revisions, session
assignment/removal, exercise confirmations, set classifications, explicit load
corrections, measurements, catalog additions and saved manual starting loads.
Failed operations do not discard the shared input cache. `add_full_session()`
delegates to the same invalidating workout writer rather than invalidating twice.

Read scopes use a `ContextVar`, with engine identity and service arguments in
their keys. Nested services reuse the scope; exit, early return and exceptions
discard it. Results are never retained between reruns or shared between concurrent
render contexts. Callers treat the returned collections as read-only.

SQLAlchemy listeners invalidate scoped reads before writes and again when a
written transaction commits or rolls back. Closing an ordinary read connection
does not clear the scope. Listeners are installed once before the application
engine is published, and consult the current context rather than retaining a
user's cache. They are not attached/detached on every render while other threads
may be executing queries. Caller-owned transaction adapters remain supported.

Direct database changes made outside `DataManager` require clearing `load_data`
or waiting for its five-minute expiry. Plan/recommendation readers still start
fresh on the next render. A read scope is reuse within a render, not a database
transaction-isolation guarantee for concurrent external edits.

## Measured results

Times are milliseconds. Cold is one cache-cold sample; warm is the median
of three samples. SQL counts include schema inspection. Values show
**stage 3 → stage 4**; individual samples and SQL execution times are in the JSON.

### Existing PostgreSQL

| Route | Cold time | Warm time | Warm SQL count |
| --- | ---: | ---: | ---: |
| Overview | 11126.7 → 5763.1 | 7922.5 → 2831.6 | 128 → 28 |
| Analysis: plan exercise progress | 7341.7 → 4502.6 | 4167.1 → 2178.8 | 70 → 23 |
| Analysis: recorded exercises | 2571.8 → 2444.4 | 86.6 → 89.9 | 0 → 0 |
| Analysis: plan consistency | 6595.3 → 4450.0 | 4211.1 → 2171.8 | 70-71 → 23 |
| Analysis: muscle map | 4778.2 → 4252.7 | 1154.7 → 1104.0 | 15 → 12 |
| Analysis: set allocation | 3636.4 → 3287.4 | 1157.9 → 1160.8 | 15 → 12 |
| Analysis: body measurements | 2415.1 → 2439.8 | 28.8 → 33.7 | 0 → 0 |
| Plan | 4817.3 → 3206.0 | 2621.3 → 902.2 | 45 → 11 |
| History | 10044.0 → 4336.5 | 3806.8 → 2220.5 | 61 → 22 |
| Change upcoming workout | - | 7485.0 → 2801.8 | 128 → 28 |

### Synthetic SQLite

| Route | Cold time | Warm time | Warm SQL count |
| --- | ---: | ---: | ---: |
| Overview | 1222.6 → 1234.9 | 291.4 → 253.9 | 80 → 28 |
| Analysis: plan exercise progress | 1473.5 → 696.1 | 331.5 → 240.0 | 46 → 23 |
| Analysis: recorded exercises | 517.4 → 482.1 | 71.7 → 69.8 | 0 → 0 |
| Analysis: plan consistency | 703.1 → 547.1 | 180.6 → 136.9 | 46 → 23 |
| Analysis: muscle map | 1218.0 → 1203.4 | 88.7 → 91.2 | 15 → 12 |
| Analysis: set allocation | 571.0 → 575.8 | 115.7 → 125.3 | 15 → 12 |
| Analysis: body measurements | 415.0 → 431.5 | 27.9 → 26.7 | 0 → 0 |
| Plan | 418.0 → 436.0 | 29.3 → 29.2 | 21 → 11 |
| History | 473.3 → 469.6 | 69.6 → 69.5 | 26 → 16 |
| Change upcoming workout | - | 288.1 → 217.3 | 80 → 28 |

Live warm Overview elapsed time fell by 64.3%, and workout switching by
62.6% in this capture. Both perform 28 rather than 128 SQL executions
(78.1% fewer). Shared schema availability is inspected once per render.
Unchanged routes with zero warm SQL remain subject to local rendering noise;
small time changes on those routes are not attributed to query optimization.

Pure calculation functions are unchanged. Their direct timings remain in the
JSON as workload context, without claiming an algorithmic speed improvement.

## Validation

The full local suite reported **560 passed, 6 skipped** in 59.4 seconds.
The six PostgreSQL integration tests require `TEST_POSTGRES_URL`, which was not
configured locally. Live read-only captures are not substitutes for those
write/migration integration cases.

The seven frozen semantic sections remain unchanged, including history-derived
starting loads, bodyweight conventions, mixed per-set loads, changed targets,
future-record exclusion, deload and return behavior. The nine captured synthetic
page outputs also match the pre-optimization outputs. Cold and warm reruns
continue to agree within every measured case.

New regression coverage checks scoped/uncached semantic equivalence, bounded
query counts as version history grows, repeated-history reuse, independent
contexts/engines, concurrent renders, cleanup after exceptions, raw writes,
rollback, schema changes and caller-owned transaction adapters. Integration
workflows verify refreshed input after workout entry, load/classification
correction, measurements, deletion, plan changes and session assignment/removal;
saved manual defaults also refresh within the same render.

All benchmark captures use database-level read-only protection and before/after
table fingerprints. The existing application retains 2531 recorded sets. A
separate user-confirmed exercise replacement was saved during this stage before
the final captures; this intentionally changes coverage in the live data.
Live chart hashes are therefore not used to claim equivalence to the older
dataset. Synthetic references provide the unchanged-data behavior check.

## Reproduce

```powershell
python -m pytest
python scripts/benchmark_project.py --output .cache/baseline/current.json
python scripts/benchmark_project.py --live --output .cache/baseline/current-live.json
```

Run benchmarks after the test process has finished to avoid local CPU contention.
The runner records the source commit and whether the working tree has changes.
Measurement limitations, including read-only setup overhead and exclusion of
browser rendering, are the same as in the stage 3 report. Three warm samples
establish a working comparison; they do not establish a latency guarantee.
