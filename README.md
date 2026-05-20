# Workout Progress Analyzer

A Streamlit analytics dashboard for tracking strength training, exercise
progress, training fatigue, body composition, and body measurements. The app is
structured around a testable metrics layer so the UI renders precomputed data
instead of owning business logic.

Live app: <https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app>

## Features

- workout session overview: volume, set count, intensity, and duration,
- exercise metrics: total volume, estimated 1RM, strength trends, and exposure,
- body-part analysis using detailed exercise-to-muscle mappings,
- body-part heatmap based on weekly training volume,
- fatigue monitoring based on RIR, failure sets, intensity, and volume,
- progress analysis for improving, stagnating, and regressing exercises,
- body metrics: weight, muscle mass, body fat, measurements, and proportions,
- TXT workout import from the sidebar.

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

Core rule: views do not calculate metrics. Data is loaded, mapped into
`MetricsInput`, processed by `metrics.metrics_engine.compute_all_metrics`, and
then rendered by the UI.

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

- Python 3.12 or newer
- a database available through `DATABASE_URL`
- dependencies from `requirements.txt`

Minimal `.env` example:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

Do not commit `.env` or database credentials. For Streamlit Cloud, set the same
value in app settings under **Secrets**:

```toml
DATABASE_URL = "postgresql+psycopg2://user:password@host:5432/database"
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
computes all metrics, and exposes these sections:

- Main Dashboard
- Exercises
- Body Parts
- Analytics
- Body Metrics

## Tests

The test suite uses `pytest` and covers mappers, domain models, the metrics
layer, month filtering, and pure UI helpers.

```bash
python -m pytest
python -m compileall -q db metrics models ui streamlit_app.py data_loader.py data_manager.py mapper.py
```

## TXT Workout Import

The importer expects this format:

```text
Godzina: 10:30 - 12:45

1. Bench Press
10x100 / 8x110 / 6x115
RIR: 2 / 1 / 0

2. Row
12x60 / 10x65
RIR: 3 / 2
```

If an exercise is missing from the database, the app shows similar exercise
names and lets the user select an existing exercise or add a new one.

## Design Principles

- metrics are pure functions without Streamlit dependencies,
- domain models are immutable (`dataclass(frozen=True)`),
- database access is separated from calculation logic,
- the UI renders prepared data and does not own business rules,
- tests verify behavior instead of implementation details.

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
