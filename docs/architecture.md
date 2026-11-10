# Architecture and data ownership

This is the maintained map of the application after cleanup stages 4–7.
Historical changes and measurements live in the [archive](archive/README.md).

## Entry points and routes

`streamlit_app.py` configures the page, loads shared input and renders one route
inside a read scope. All routes initially share `data_loader.load_data()`.

| Route | Presentation and calculation ownership |
| --- | --- |
| Overview | `OverviewView`, `NextWorkoutView`, `TrainingInsightsView`; prepared recommendations and recent observations |
| Analysis | `AnalysisView`; recorded exercise or plan-context performance, plan consistency, muscle allocation and measurement timelines |
| Plan | `TrainingPlanView`; versioned routine drafts and training-block configuration |
| History | `HistoryView`, `PlanScheduleView`; entry/import, linking, replacements, set/load corrections and measurement entry |

`ExerciseView.render()` and `BodyMetricsView.render()` each have one active
display path. History calls the existing body-measurement form for entry.
`metrics.utils.dates.to_date` is the shared date utility.

## Boundaries

```mermaid
flowchart TD
    UI[Streamlit views] --> Facade[DataManager]
    Facade --> Services[Application services]
    Facade --> DB[Database readers and writers]
    Services --> DB
    Services --> Metrics[Pure calculations]
    DB --> Mapper[Row mapping]
    Mapper --> Models[Domain models]
    Metrics --> Models
```

Views own widgets, navigation and presentation. `DataManager` provides the
UI-facing API, chooses the configured engine and invalidates cached
input after successful writes. SQL belongs to `db/`. An explicit
`DataManager(engine=...)` supports isolated callers without loading database
configuration. Existing zero-argument construction remains supported.

`services/` coordinates reads and decisions; it does not contain Streamlit
widgets or database statements. `db/` owns query construction and transactions.
`mapper.py` converts rows into domain objects without opening connections.
`metrics/` and `models/` do not import storage, application services or UI modules.
Architecture tests protect these calculation/model boundaries.

## Prepared recommendation inputs

[`services/recommendations.py`](../services/recommendations.py) has three main
operations:

1. `prepare_plan_context` loads version snapshots and complete linked history
   for a requested plan and date window. Earlier history and early recordings
   of future planned slots remain available through the existing performance
   reader. Supplied version snapshots must belong to the selected plan.
2. `PlanReadContext.prepare_workout` selects an actual scheduled workout from
   that context. It returns a `PreparedWorkout` with the same history, versions
   and explicit evidence cutoff. The immutable types live in
   [`models/plan_context.py`](../models/plan_context.py).
3. `recommend_prepared_workout` applies the existing pure progression engine,
   then the separate exact-exercise starting-history fallback where applicable.
   A confirmed alternative reuses the prepared input and supplies its own
   exercise ID and equipment step.

Overview prepares one context covering its history and four-week preview
window. Next-workout selection, ordinary targets, alternative previews and
attention annotations share those inputs. The annotation date filter still
selects the recent 28 days by actual execution date. Future preview slots do
not extend the evidence cutoff or admit future logs.

The next-workout view uses the prepared workout's target identities.
`metrics/recommendation_history.py` owns the pure selection of confirmed alternatives.

Contexts are local variables rebuilt for each render. They are not written to
the database or retained in session state. Existing write invalidation and
new-render refresh remain unchanged. Callers should prepare a new context
after changing source data instead of keeping an old snapshot across writes.

## Recorded history and mapping

[`db/recorded_workouts.py`](../db/recorded_workouts.py) owns recorded-exercise
table descriptions and `load_recorded_exercises`. The reader accepts a
caller-owned connection, session IDs and an optional exact exercise-ID filter.
It reads working/warm-up corrections and optional explicit load snapshots,
without making plan matches or choosing progression evidence.

Plan adherence, usable starting-load history and raw recommendation references
share that reader with distinct selection policies:

| Consumer | Selection policy |
| --- | --- |
| Plan adherence/performance | Linked sessions and explicit exercise confirmations |
| Starting-load history | Exact exercise across plans; ordinary usable records up to the cutoff |
| Manual-start references | Entries in the latest raw session, including unlinked records |

`mapper.map_recorded_exercises` groups the returned rows and delegates each set
to `map_workout_set`. It preserves repeated exercise entries, empty entries,
per-set loads, missing RIR, timed sets and correction flags. `data_loader`
assembles `MetricsInput` through the same row mappers and one shared input cache.

## Workout persistence and shared dates

[`db/workout_sessions.py`](../db/workout_sessions.py) owns complete workout
entry/import persistence. All exercises, sets, load snapshots and explicit
classifications are written in one transaction. Same-day appending, ID/name
resolution and rollback behavior retain their existing contracts. `DataManager`
delegates to it and refreshes the shared input cache only after success.

DataFrame readers for exercise mappings and raw workout-exercise identities
live in `db/queries.py`, including the optional-mapping fallback for older schemas.
`DataManager` delegates SQL, transaction control and row mapping to their owners.

[`metrics/utils/dates.py`](../metrics/utils/dates.py) owns `to_date`. Measurement
timelines, period selection and data filters use this utility directly. It accepts
native dates, datetimes, pandas timestamps and ISO strings.

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

## Data model

A **session** contains performed **exercises**, and each exercise contains
**sets**. The catalog maps exercises to muscle groups. Optional side tables
store explicit load details and set-purpose corrections.

Plans have dated versions, so an old session can be interpreted against the
prescription that applied then. Body measurements form independent time series;
they do not need a workout on the same date.

<details>
<summary>Core database relationships</summary>

```mermaid
erDiagram
    workout_sessions ||--o{ workout_exercises : contains
    exercises ||--o{ workout_exercises : identifies
    workout_exercises ||--o{ workout_sets : has
    exercises ||--o{ exercise_muscle_map : targets
    workout_sets ||--o| workout_set_loads : load_details
    workout_sets ||--o| workout_set_classifications : correction
    training_plans ||--|{ training_plan_versions : versions
    training_plan_versions ||--o{ training_plan_days : workouts
    training_plan_days ||--o{ training_plan_exercises : prescribes
    training_plan_versions ||--o| training_plan_progression : block_settings
```

| Tables | Stored information |
| --- | --- |
| `workout_sessions`, `workout_exercises`, `workout_sets` | Dates, performed exercises, reps/time, weight and RIR. |
| `workout_set_loads` | Explicit load type, per-set body mass and assistance. Added weight stays in `workout_sets`. |
| `workout_set_classifications` | Optional Working / Warm-up exceptions. |
| `exercises`, `exercise_muscle_map` | Catalog and muscle roles/factors. |
| `training_plans`, `training_plan_versions` | Stable plan identity and dated snapshots. |
| `training_plan_days`, `training_plan_exercises` | Named weekdays, order, sets, ranges, unit, RIR and weight step. |
| `training_plan_progression` | Versioned block start and length. No row means unconfigured. |
| `training_plan_session_links`, `training_plan_exercise_matches` | Planned-slot assignments and session-specific replacements. |
| `training_plan_exercise_lineage` | Stable history keys for plan positions across compatible revisions. |
| `recommendation_starting_loads` | Remembered manual fallback values, separate from performed sets. |
| `exercise_history_load_settings` | Exercise-specific confirmations of legacy body-mass conventions. |
| `schema_migrations` | Applied additive migration revisions. |
| `body_composition`, `body_measurements` | Weight/composition and body circumferences over time. |

Versions append a complete snapshot. Each starts after the previous version's
start date and cannot be backdated. Future versions do not alter earlier dates.
Multiple workouts may share a weekday; an exercise may have different targets
in different workouts.

Developer entry points:
`DataManager.save_training_plan(draft, plan_id=...)` appends a revision;
`load_training_plans()` lists latest snapshots, including future ones;
`load_effective_training_plan(plan_id, on_date)` resolves a particular date.
Draft types live in `models/training_plan.py`.

</details>

## Public recommendation API and compatibility

`DataManager.load_workout_recommendations(plan_id, day_id, scheduled_date, as_of=...)`
returns immutable `WorkoutRecommendation` and per-exercise targets, including
dates, block phase, source IDs, limitations and the rules version.
`services.recommendations` coordinates prepared inputs and the pure
`metrics.progression.recommend_workout` engine for arbitrary dates.

`db.progression` intentionally re-exports the service entry points for existing
callers. Its `load_normal_workout_recommendations` wrapper rejects deload dates.
Existing recorded-table exports in `db.plan_adherence` and the load-type export
in `ui.utils.set_load_inputs` are also intentional. New storage callers use
`db.recorded_workouts` directly. These facades do not restore the retired
aggregate metrics engine or the old input builder.

For behavior, read the [calculation rules](calculation-rules.md) and
[recommendation rules](progression-rules.md). For installation and explicit
migration commands, use [local setup](getting-started.md).

## Fresh-install schema and demo data

`db.schema.define_base_tables` owns the seven base catalog, workout, mapping
and body-tracking tables for new installations. `db.bootstrap` creates those
tables in an empty target schema, applies the existing nine migrations and
optionally calls `db.demo_data` within the same transaction. The resulting
twenty-table schema supports the normal readers, writers and views.

Bootstrap requires an explicit URL and refuses existing tables/views. It runs
only as a CLI operation, outside application startup. Existing installations
continue through `db.migrate`; their applied revisions are unchanged.
Demo values come from constants and offline exercise mappings, with dates
relative to a supplied reference date or today. No personal dataset is read.

SQLite is the local demo backend. Application connections enable foreign keys,
workout time parameters use SQLAlchemy's time type, and catalog writes use
PostgreSQL's table lock only on PostgreSQL. The transaction's existing read-cache
and input-cache invalidation rules still apply to both backends. Setup commands
and target selection live in [local setup](getting-started.md).
SQLite transaction and foreign-key handling follow the
[SQLAlchemy dialect guidance](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#transactions-with-sqlite-and-the-sqlite3-driver).

## Container startup

`compose.yaml` defines an application image and PostgreSQL 16 with a persistent
named volume. The app waits for database health, then `db.container_start`
prepares the database before replacing its process with Streamlit. Empty
targets reuse `db.bootstrap` and the synthetic seed; recognized installations
receive pending migrations without replacing records or regenerating examples.
Initialization uses the same transaction and migration lock as the standalone
bootstrap. Ordinary Streamlit startup outside this launcher does not initialize
or migrate databases.

`Dockerfile` installs only runtime requirements and application files, runs
without root and exposes an HTTP health check. `.dockerignore` restricts the
build context; Compose sets an internal database URL rather than inheriting
the host's application connection. The runtime image has no source bind mounts.
Commands and data-volume behavior are owned by the [Docker guide](docker.md).

## Inspect the module graph

```powershell
python scripts/project_inventory.py
python scripts/project_inventory.py --json
```

The standard-library script inspects Git-tracked Python source without importing
the application or connecting to the database. Counts describe the checkout
where it runs. Import reachability includes conditional/function imports and
literal AppTest scripts; it does not prove every branch executes. Source size
and test totals in archived reports belong to their measured commits.
