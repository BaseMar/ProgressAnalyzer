# Gym Progress Analyzer

A Python-based analytics application for tracking and analyzing gym training progress.
The project focuses on clean data modeling, reproducible metrics, and separation of concerns
between data access, analytics, and UI.

## Key Features

- Workout session tracking (sets, reps, volume, intensity, RIR)
- Exercise-level strength and volume progression
- Training frequency and fatigue analysis
- Body composition and measurement trends
- Correlation analysis between volume, intensity, and strength
- Interactive dashboard for data exploration

## Architecture Overview

The project follows a layered architecture:

```
UI (Streamlit)
│
├── Services (application logic)
│
├── Metrics (pure analytics, stateless)
│
├── Models (dataclasses, domain objects)
│
└── Database (SQL Server)
```

### Core Principles

- **UI does not compute metrics**
- **Services orchestrate data flow**
- **Metrics are pure, deterministic functions**
- **Models reflect database structure**
- **No business logic inside the database layer**

---

## Project Structure

```
Analizator progresu na siłowni
├─ app.py
├─ data_loader.py
├─ data_manager.py
├─ db
│  ├─ connection.py
│  └─ queries.py
├─ mapper.py
├─ metrics
│  ├─ body_metrics.py
│  ├─ correlation_metrics.py
│  ├─ exercise_metrics.py
│  ├─ fatigue_metrics.py
│  ├─ frequency_metrics.py
│  ├─ input.py
│  ├─ input_builder.py
│  ├─ metrics_engine.py
│  ├─ progress_metrics.py
│  ├─ registry.py
│  ├─ session_metrics.py
│  ├─ set_metrics.py
│  ├─ utils
│  │  ├─ strength.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ models
│  ├─ body.py
│  ├─ body_composition.py
│  ├─ body_measurement.py
│  ├─ exercise.py
│  ├─ muscle_group.py
│  ├─ workout_exercise.py
│  ├─ workout_session.py
│  ├─ workout_set.py
│  └─ __init__.py
├─ README.md
├─ requirements.txt
└─ ui
   ├─ analytics_view.py
   ├─ body_parts_view.py
   ├─ dashboard_view.py
   ├─ exercise_view.py
   ├─ sidebar_upload.py
   ├─ sidebar_view.py
   └─ utils
      ├─ data_filter.py
      └─ exercise_matcher.py

```

---

## Metrics Engine

All analytics are computed through a centralized metrics engine.

- Each metric module exposes a single `compute_*` function
- Metrics are registered in a registry
- The engine executes all metrics in a deterministic order

This design allows:
- Easy extensibility
- Clear testing boundaries
- No coupling between metrics

---

## Tech Stack

- Python 3.11+
- Pandas
- SQLAlchemy
- Microsoft SQL Server
- Streamlit

---

## Future Improvements

- Automated tests for metrics
- Caching layer for expensive analytics
- ML-based progression prediction
