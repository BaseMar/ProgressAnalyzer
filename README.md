# Workout Progress Analyzer

A full-stack data analytics dashboard for strength training progress, fatigue,
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
major improvements are database migrations, anonymized seed data, Docker Compose
setup, and CI.

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
- **python-dotenv** for local environment configuration
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

- Session overview: volume, set count, intensity, duration, and workload.
- Exercise analytics: total volume, estimated 1RM, average RIR, exposure, and
  progress trends.
- Progress classification: improving, stagnating, and regressing exercises.
- Training frequency: sessions per week and average days between sessions.

### Fatigue & Recovery

- RIR distribution and average RIR.
- Sets to failure and failure-set ratio.
- Volume load and intensity load.
- Per-session fatigue score and high-fatigue session indicators.

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

- `Main Dashboard` - high-level training summary and recent session history.
- `Exercises` - exercise-specific performance and trend analysis.
- `Body Parts` - muscle-group volume distribution and heatmap.
- `Analytics` - progress and fatigue analysis.
- `Body Metrics` - body composition and measurement trends.

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
> database with the expected schema. The repository does not yet include full
> database migrations or an anonymized seed dataset. For quick review, use the
> live demo.

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

## Tests

The test suite uses `pytest` and covers mappers, domain models, the metrics
layer, month filtering, parser behavior, and pure UI helpers.

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
- Improve database setup documentation with migrations or schema bootstrap
  scripts.
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
