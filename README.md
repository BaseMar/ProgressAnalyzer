# Workout Progress Analyzer

An end-to-end data analytics dashboard for strength training progress, fatigue,
muscle-group volume, and body composition tracking.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Database](https://img.shields.io/badge/database-PostgreSQL%20%2F%20Supabase-blue)
![Deployment](https://img.shields.io/badge/deployment-Streamlit%20Cloud-orange)

## Table of Contents

- [Project Goal](#project-goal)
- [My Role](#my-role)
- [Live Demo](#live-demo)
- [Project Status](#project-status)
- [Preview](#preview)
- [Tech Stack](#tech-stack)
- [What It Does](#what-it-does)
- [Example Insights](#example-insights)
- [Features](#features)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Installation](#installation)
- [Tests](#tests)
- [Limitations & Future Work](#limitations--future-work)

## Project Goal

Workout logs usually show raw training history, but they rarely explain whether
a user is actually progressing, accumulating fatigue, or training muscle groups
in a balanced way.

This project turns raw workout and body-measurement data into an analytical
dashboard that helps identify:

- strength progress and regressions,
- training consistency,
- fatigue patterns,
- body-part volume distribution,
- body recomposition trends.

It also connects exercise-level performance with muscle-group exposure, so a
training log can answer not only "what did I lift?", but also "what parts of
the body am I actually training, how hard, and with what trend over time?".

## My Role

I designed and implemented the full application, including:

- relational data model for workout and body-tracking data,
- metric calculation layer for sessions, exercises, fatigue, progress, body
  parts, and body measurements,
- Streamlit dashboard UI,
- TXT workout importer with flexible parsing and exercise matching,
- automated tests for core metric logic, mappers, filters, and import helpers,
- visual analytics for progress, fatigue, muscle-group volume, and body
  composition.

## Live Demo

Live app: <https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app>

The deployed version uses anonymized personal training and body-measurement data
prepared for demonstration purposes and stored in a hosted Supabase database.
Local development uses the same application code, but requires a
PostgreSQL-compatible database configured through `DATABASE_URL`.

This is a public single-user demo, not a multi-user product with private
per-user data isolation.

## Project Status

The application is functional and deployed as a public single-user demo. Core
analytics, TXT import, database integration, and tests are implemented. The next
major improvements are a complete database
bootstrap, anonymized seed data, Docker Compose setup, and CI. Versioned plan
storage, its additive migration, and the Training Plan editor are implemented.

## Preview

![Main Dashboard overview](screenshots/Main_Dashboard_1.png)

![Analytics overview](screenshots/Analytics_1.png)

![Body parts heatmap](screenshots/Body_Parts_2.png)

## Tech Stack

- **Python 3.11+**
- **Streamlit** for the interactive dashboard UI
- **Pandas** and **NumPy** for data processing and aggregation
- **PostgreSQL** hosted on **Supabase** for persistent workout and body-tracking data
- **SQLAlchemy** with **psycopg2** for database access
- **Plotly** for interactive charts
- **Pillow** for body heatmap image processing
- **Pytest** for automated tests
- **Streamlit Community Cloud** for deployment

## What It Does

Workout Progress Analyzer is a Streamlit dashboard for tracking strength
training, recovery pressure, exercise trends, body measurements, and body
composition. It imports workout data from a database, maps it into a small
domain model, computes core metrics in a separate calculation layer, and renders
the results as focused dashboard views.

The app is built for lifters who want more than a list of completed workouts.
It highlights whether performance is moving up or down, whether volume is
distributed sensibly across body parts, and whether body composition is changing
alongside training.

## Example Insights

The dashboard can answer questions such as:

- Which exercises are improving, stagnating, or regressing?
- Which exercises generate the highest training volume or estimated 1RM?
- Which muscle groups receive the most weekly volume, and which may be
  undertrained?
- Is training fatigue increasing through more failure sets, lower RIR, or higher
  workload?
- Are high-volume sessions concentrated in specific periods or body parts?
- Is body weight changing together with muscle mass, fat mass, or body fat
  percentage?
- Are body measurements and proportions moving in the expected direction over
  time?

## Features

### Training Analytics

- Session overview: volume, set count, estimated strength, duration, and workload.
- Exercise analytics: total volume, estimated 1RM, average RIR, exposure, and
  progress trends.
- Progress classification: improving, stagnating, and regressing exercises.
- Training frequency: sessions per week and average days between sessions.

Frequency includes all ISO calendar weeks between the first and last workout in
the selected period, including weeks without workouts. Exercise and body-part
frequencies use that same observation period. Separate sessions on the same day
count separately. Dates outside that observed span are not treated as missed
training without a plan.

Progress compares the first and last non-overlapping windows of up to three
sessions, using each session's best estimated 1RM (or longest set for timed
exercises). At least two comparable sessions are required; exposures count
sessions rather than sets. These metrics describe recorded performance, not
technique, plan adherence, or muscle growth.

Exercise histories also keep same-day sessions separate. Exercise volume trends
compare total session volumes; strength and duration trends compare session bests.
A single session has no between-session trend.

### Fatigue & Recovery

- RIR distribution and average RIR.
- Sets to failure and failure-set ratio.
- Volume load and timed work.
- Per-session heuristic score and high-score session indicators.

`Mean session e1RM` is displayed in kg: it averages the session means of estimated
1RM values, rather than representing relative intensity. The fatigue chart uses
recorded dates/start times, and consecutive high-score runs follow chronological
order. High-score session shares are displayed as percentages. The 0–1 score and
its 0.7 threshold are unvalidated heuristics, not measurements of recovery.
Strength rankings use neutral `Highest change` / `Lowest change` labels, even
when every exercise improves or every exercise declines.

### Body-Part Analysis

- Weekly set volume by body part.
- Muscle-group exposure through exercise-to-muscle mappings.
- Volume distribution across trained body parts.
- Heatmap against editable target volume ranges.

### Body Metrics

- Body weight, muscle mass, fat mass, water mass, and body fat percentage.
- Measurement trends for chest, waist, abdomen, hips, thigh, calf, and biceps.
- Body proportion ratios such as chest-to-waist and thigh-to-waist.
- Recomposition quality based on weight and lean-mass change.

### Data Import

- TXT workout import from sidebar notes.
- Flexible parsing for common set, RIR, and time-range formats.
- Exercise matching for imported exercise names.
- Option to add missing exercises with inferred muscle targets.

## App Sections

- `Main Dashboard` - high-level training summary and an interactive workout calendar.
  Days with recorded workouts are marked with a dot. Select a day to see all its
  sessions, exercises, and sets. The calendar follows the sidebar month filter;
  with `All time`, use the history month selector to browse between workouts.
- `Exercises` - exercise-specific performance and trend analysis.
- `Training Plan` - build weekly routines from catalog exercises, set working
  sets and repetition/time ranges, and save successive versions with history.
- `Body Parts` - muscle-group volume distribution and heatmap.
- `Analytics` - progress and fatigue analysis.
- `Body Metrics` - body composition and measurement trends.

## Training Plan editor

Select `Training Plan` in the sidebar, then choose `Create a new plan` or an
existing plan. Plans are independent of the sidebar history month filter.

Saved plans open as weekly reference cards, with exercises available under
`Reference exercises`. Switch on `Edit as a new version` to change a saved plan.

1. Enter the plan name and effective date.
2. Add named workouts and choose their weekdays. Select one `Workout to edit`.
3. Add exercise cards from the catalog. Set the number of sets, minimum/maximum,
   and measurement unit. For example, 3 sets with 6–10 reps.
4. Use the arrow buttons to reorder exercises. Target RIR is optional and collapsed.
5. Save the plan. All workout cards are saved together; editing an existing plan
   appends a version with a later start date. Previous versions remain available.

The plan editor requires migration 001 described below. Calendar assignments
require migration 002; execution analysis and confirmed replacements require
migration 003. Progression recommendations are not yet calculated.
Native tables and inputs use the shared dark/teal theme in `.streamlit/config.toml`.

## Planned workouts in the calendar

In `Main Dashboard`, select a `Calendar plan` to overlay its weekly schedule.
Choose `Workout history only` to hide the overlay. With the sidebar set to
`All time`, the calendar also lets you browse future months. Each date uses the
version effective on that date, so old workouts retain their original targets.

- A bottom dot marks the actual day of recorded training.
- A top-right amber ring marks a planned workout. The ring becomes filled teal
  when all planned slots on that date have a session linked to them.
- Select a planned day, choose the actual recorded date, then choose and link its
  session. Other dates/months remain available for moved workouts. The calendar
  shows assignment status and workout history, without analysis tables.
- One recorded session can be linked to one planned slot across all plans. A slot
  accepts one session. Remove the existing link before correcting an assignment.
- Removing a link preserves the workout log. Deleting a recorded session removes
  its link and leaves its planned slot unlinked.

Linking identifies which workout was performed; it does not mark every planned
exercise/set as completed. Future unlinked slots are simply planned, not missed.
New plan versions cannot supersede already linked slots: remove those links or
choose a later effective date. Calendar slots are generated when viewed rather
than materializing an unlimited recurring schedule in the database.

## Plan execution and exercise replacements

`Analytics` has separate tabs for Plan execution, Overall strength and Fatigue.
Plan execution replaces Plateau Zone Analysis.
Select a plan; the sidebar month filter sets the scheduled date range. Actual
sessions linked from other dates/months are still loaded in full.

The overview shows three percentages: workouts with linked logs, planned sets
logged, and logged sets within the target range. The last indicator uses recorded
sets as its denominator, rather than penalizing absent logs twice. A weekly
stacked chart distinguishes full, partial, unmatched and unlinked workouts. One
short observation highlights the largest gap in logged sets.

Summary ratios include only scheduled dates before today. Today's open workouts
and future slots neither lower nor inflate them. A moved workout counts as
recorded, but not on the planned day. Unlinked workouts are not proof of absence.
Timing, data quality and auditable source rows live under `Definitions & source
data`, rather than expanding the main overview.
Coverage excludes explicitly labelled warm-ups and caps credit at
the planned count per position. Coverage alone does not indicate success against
the repetition/time range or RIR; these are checked separately below. Technique
and muscle growth are not assessed.

In Analytics, expand `Exercise replacements & data corrections`, choose the linked
workout and planned exercise, then explicitly confirm the actual exercise. For
example, Machine Chest Press can cover the planned Barbell Bench Press position.
This approval applies to that session only; the plan and actual exercise identity
remain unchanged. Their strength histories are never combined.

Only matching catalog IDs are automatic. Muscle-group similarity does not imply
approval. A confirmed replacement reserves that recorded exercise for one plan
position; its sets cannot also cover another position. Repeated exact-ID plan
positions share the remaining logged sets without double counting. Replacements
must use the same measurement unit (repetitions or seconds) as the planned target.
Removing a replacement restores exact matching. Unlinking/deleting the session
also removes its approvals, while unlinking preserves the workout log.

## Exercise target checks and previous performance

Exercise analysis lives only in Analytics. Select one workout/exercise context
under `Exercise trends` to see its latest observation, range/RIR result and chart.
Mean repetitions/time and mean load are shown separately. The shaded target band
applies to the mean; the hover shows the number of individual sets within range,
so the mean alone should not be read as proof that all sets met the target.
Session points are equally spaced by execution order, not elapsed calendar time.
Range boundaries are inclusive. Missing RIR stays unknown; logged zero stays zero.

Expand `Previous vs current · set breakdown` for a compact three-column comparison
of credited sets. Earlier history remains available outside the
visible month. Ordering uses recorded session date, start time and session ID,
not the planned date; unknown start times sort first and IDs break remaining ties.

Comparisons require the same plan workout name, weekday and order, exercise
position, planned and actual catalog IDs, measurement unit, set count, target
range and target RIR. Identical targets can be compared across plan versions;
context changes start a new history. Approved substitutes compare only with the
same substitute previously used in that plan context, never with the original.
Unlinked workouts and other plan contexts are not used as a fallback baseline.

At equal per-set loads, the app reports the change in total repetitions or time.
Changed loads or incomplete executions show both results without an automatic
improvement/regression label. Mean RIR changes require complete RIR data in both
executions. These are observed comparisons, not weight recommendations or a
judgment that training was physiologically effective. Unknown set types remain
included until classified; labelled warm-ups are excluded from these checks.

## Working sets and warm-ups

Apply migration 004 to enable set classification. Existing sets remain `Unknown`;
no type is inferred from load, exercise order or date. In `Analytics` → `Fatigue`,
expand `Working sets & warm-up labels`, select a session and edit its set types:

- `Working` — explicitly included in analysis.
- `Warm-up` — preserved in history but excluded from set, session, exercise,
  strength-progress, fatigue and plan-coverage calculations and exercise charts.
- `Unknown` — included for historical continuity, with its uncertainty disclosed.

Save the labels to recalculate analyses. Changing a label back to `Unknown` removes
the explicit classification. Calendar log totals still include all recorded sets;
warm-ups carry a `WU` badge. Training-visit frequency still counts recorded sessions.

TXT import accepts explicit markers, including mixed markers on one line:

```text
1. Bench Press
Warm-up: 10x20 / 8x40
Working: 8x60 / 8x60
RIR: 4 / 3 / 2 / 1
```

`Rozgrzewka:` and `Robocze:` are also supported. Unmarked tokens stay unknown.
Classification is stored separately from the original set values.

## TXT Workout Import

The sidebar importer accepts structured workout notes such as:

```text
Godzina 15:35-16:50

1. Incline Dumbbell Press
10x24/10x24/6x26
RIR 2/2/0

2. Lat Pulldown
12x70 / 10x70 / 11x70
RIR: 1 / 0 / 0
```

It also supports common variants:

- time ranges like `Godzina: 10:30 - 12:45`, `Godz. 15.35 do 16.50`, or
  `15:35-16:50`,
- numbered exercises written as `1.`, `1)`, or `1 -`,
- inline exercise entries like `Bench Press: 10x100/8x110 RIR 2/1`,
- set formats such as `10x100`, `10 x 100 kg`, `10*100`, and `10 @ 100`,
- comma decimal weights such as `67,5`,
- missing RIR values, which are imported as empty instead of dropping the whole
  exercise.

If an imported exercise is not found in the database, the app suggests similar
existing exercise names and allows the user to select one or add a new exercise.

## Key Technical Decisions

- Separated metric calculation from the Streamlit UI to keep business logic
  testable.
- Used immutable domain models to make data flow predictable.
- Built a central metrics engine to compute all dashboard metrics from one
  structured input.
- Kept database access isolated in the `db/` and `data_manager.py` layers.
- Added tests for metric calculations, filtering logic, data mapping, and TXT
  import parsing.

## Data Flow

```text
Database
  -> DataManager / SQL queries
  -> Data Loader
  -> Domain Models / MetricsInput
  -> Metrics Engine
  -> Streamlit Views
```

Workout and body-tracking records are read from the database, normalized into
domain models, passed through one structured `MetricsInput`, and then consumed
by the dashboard views as precomputed metrics.

## Architecture

The project is split into clear layers:

```text
streamlit_app.py
  -> ui/                 # Streamlit views and presentation helpers
  -> metrics/            # pure metric calculation logic
  -> data_loader.py      # maps database data into domain models
  -> data_manager.py     # high-level data operations
  -> db/                 # database connection and SQL queries
  -> models/             # immutable domain models
```

Core rule: the main metric formulas live outside the UI. Data is loaded from the
database, mapped into `MetricsInput`, processed by
`metrics.metrics_engine.compute_all_metrics`, and then rendered by the UI. Views
may still perform presentation-level reshaping, filtering, or aggregation needed
for a specific chart or table.

## Data Model

Training data uses:

- `workout_sessions`
- `workout_exercises`
- `workout_sets`
- `exercises`
- `exercise_muscle_map`

Training-plan snapshots use:

- `training_plans` — stable identity of a plan.
- `training_plan_versions` — name, version number, and effective date.
- `training_plan_days` — named workouts, weekdays (Monday = 0), and order.
- `training_plan_exercises` — catalog exercise IDs, order, sets, target range,
  target unit (`reps` or `seconds`), optional RIR and weight increment.
- `training_plan_session_links` — a recorded session assigned to one dated
  workout template; uniqueness prevents counting a session or planned slot twice.
- `training_plan_exercise_matches` — explicit session-scoped approval connecting
  a planned exercise position to a recorded exercise entry.

Edits through the storage API append a complete snapshot. Each new version starts
after the previous version's start date and cannot be backdated. Its effective
date ends the previous version's interval. Future versions do not affect the plan
resolved for earlier dates. Multiple workouts may share a weekday, and an exercise
may have different targets in different workouts. Existing sessions are not
automatically assigned to a plan. Plans currently follow the single-user data
model of this project.

Body tracking data uses:

- `body_composition`
- `body_measurements`

## Data Model Diagram

```mermaid
erDiagram
    workout_sessions ||--o{ workout_exercises : contains
    exercises ||--o{ workout_exercises : is_performed_as
    workout_exercises ||--o{ workout_sets : has
    exercises ||--o{ exercise_muscle_map : targets

    workout_sessions {
        int session_id PK
        date session_date
        time start_time
        time end_time
    }

    workout_exercises {
        int workout_exercise_id PK
        int session_id FK
        int exercise_id FK
    }

    workout_sets {
        int set_id PK
        int workout_exercise_id FK
        int set_number
        int repetitions
        float weight
        int rir
    }

    exercises {
        int exercise_id PK
        string exercise_name
        string category
        string body_part
    }

    exercise_muscle_map {
        int exercise_id FK
        string muscle_group
        string muscle_name
        string role
        float set_factor
    }

    body_composition {
        date measurement_date
        float weight
        float muscle_mass
        float fat_mass
        float body_fat_percentage
    }

    body_measurements {
        date measurement_date
        float chest
        float waist
        float hips
        float thigh
        float calf
        float biceps
    }
```

`body_composition` and `body_measurements` are independent time-series tables.
They are analyzed alongside workout sessions, but they do not need a direct
foreign-key relationship to a specific training session.

`exercise_muscle_map` supports multiple muscle targets per exercise:

- `exercise_id`
- `muscle_group`
- `muscle_name`
- `role` (`primary`, `secondary`, `stabilizer`)
- `set_factor`

Default volume attribution weights:

- `primary`: `1.0`
- `secondary`: `0.5`
- `stabilizer`: `0.25`

Seed the exercise-muscle mapping with:

```bash
python -m db.seed_exercise_muscle_map
```

## Requirements

- Python 3.11 or newer
- PostgreSQL-compatible database available through `DATABASE_URL`
- dependencies from `requirements.txt`

> Note: Local setup currently requires an existing PostgreSQL-compatible
> database with the expected workout/body-tracking schema. The repository includes
> an additive migration for training plans, but not a full bootstrap of the legacy
> schema or an anonymized seed dataset. For quick review, use the live demo.

Minimal `.env` example:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

## Installation

```bash
git clone https://github.com/BaseMar/ProgressAnalyzer.git
cd ProgressAnalyzer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running The App

```bash
streamlit run streamlit_app.py
```

On startup, the app loads data from the database, builds `MetricsInput`,
computes all metrics, and renders the dashboard sections.

If `DATABASE_URL` is missing or points to a database without the expected
tables, the app will fail during startup data loading.

## Training-plan database setup

Use the existing PostgreSQL database configured by `DATABASE_URL`. Migration 001
creates the new plan tables and a `schema_migrations` ledger; it requires the
existing `exercises` table. Migration 002 adds session links and requires
`workout_sessions`. Migration 003 adds confirmed exercise matches and requires
`workout_exercises`. Migration 004 adds explicit set classifications and requires
`workout_sets`. These migrations do not change existing workout records.
Migrations are never run automatically at application startup.

Preview pending migrations (read-only):

```bash
python -m db.migrate
```

Apply pending migrations explicitly:

```bash
python -m db.migrate --apply
```

Successful revisions are recorded and skipped on subsequent runs. PostgreSQL
applies each run in a transaction with a migration lock. An untracked conflicting
table causes an error rather than being silently adopted.

The storage API is available through `DataManager.save_training_plan(draft)`;
pass `plan_id` to append a revision. `load_training_plans()` lists the latest saved
version of each plan (including future versions). Use
`load_effective_training_plan(plan_id, on_date)` to resolve the version applicable
on a specific date. Drafts use immutable types from `models/training_plan.py`.

## Tests

The test suite uses `pytest` and covers mappers, domain models, the metrics
layer, month filtering, parser behavior, and pure UI helpers.

Plan tests use an isolated SQLite database with foreign keys and transactional DDL
enabled. They cover migration repeatability, snapshot roundtrips, effective-date
boundaries, database constraints, and atomic rollback. PostgreSQL DDL compilation
is checked, but these tests do not replace validation on a PostgreSQL test database.

```bash
python -m pytest
python -m compileall -q db metrics models ui streamlit_app.py data_loader.py data_manager.py mapper.py
```

## Design Principles

- Metrics are pure functions without Streamlit dependencies.
- Domain models are immutable (`dataclass(frozen=True)`).
- Database access is separated from calculation logic.
- The UI renders prepared data and keeps business rules out of view classes.
- Tests verify behavior instead of implementation details.

## Limitations & Future Work

- The current live deployment is a public single-user demo backed by one hosted
  database, not a production multi-user SaaS application.
- Add an anonymized seed dataset for local development, tests, and screenshots
  without relying on the hosted Supabase database.
- Add a Docker Compose setup for repeatable local development with a database.
- Add a CI pipeline for automated tests, linting, and import-parser regression
  checks.
- Extend the additive plan migrations into a complete legacy database bootstrap.
- Extend analytics with prediction-oriented features, such as estimated progress
  trajectory or fatigue-risk signals.
- Add user authentication and data isolation before treating the app as a
  multi-user product.
- Continue improving TXT import coverage for more free-form workout note styles.

## Screenshots

### Sidebar

![Sidebar navigation and filters](screenshots/SideBar.png)

### Main Dashboard

![Main Dashboard overview](screenshots/Main_Dashboard_1.png)
![Main Dashboard session history](screenshots/Main_Dashboard_2.png)

### Exercises

![Exercises summary](screenshots/Exercises_1.png)
![Exercise details](screenshots/Exercises_2.png)

### Body Parts

![Body parts overview](screenshots/Body_Parts_1.png)
![Body parts heatmap](screenshots/Body_Parts_2.png)
![Body parts details](screenshots/Body_Parts_3.png)

### Analytics

![Analytics overview](screenshots/Analytics_1.png)
![Fatigue analytics](screenshots/Analytics_2.png)
![Progress analytics](screenshots/Analytics_3.png)

### Body Metrics

![Body metrics snapshot](screenshots/Body_Metrics_1.png)
![Body composition trends](screenshots/Body_Metrics_2.png)
![Body measurement trends](screenshots/Body_Metrics_3.png)
![Body proportions](screenshots/Body_Metrics_4.png)
