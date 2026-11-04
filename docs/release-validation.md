# Progression update: final verification

Verification date: **4 November 2026**. The update is published through `main` to
the existing [Streamlit Cloud app](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).
Streamlit is pinned to **1.66.1** in `requirements.txt`.

## Verified behavior

| Check | Result |
| --- | --- |
| Unit, SQLite, parser and Streamlit interaction tests | 230 passing cases |
| Isolated PostgreSQL integration | 5 passing cases, all fixture schemas rolled back |
| Production schema migration preview | No pending migrations; revisions 001–005 already applied |
| Main Dashboard, Training Plan, Exercises, Body Parts, Analytics and Body Metrics | All six pages loaded against the configured PostgreSQL database without exceptions or error messages |
| Live Cloud version and dropdowns | Streamlit 1.66.1; correct option colors, hover/selection and body-level portal styles |
| Long lists and keyboard interaction | Browser checks on Streamlit 1.51.0 and 1.66.1; native scrolling retained |
| Published Analytics | Next workout card and recorded plan indicators loaded successfully |
| Python compilation and whitespace validation | Passed |

PostgreSQL checks create a unique schema in a transaction, define only the legacy
tables needed by the plan services, apply migrations 001–005, and generate
synthetic workouts there. The transaction is rolled back and schema removal is
asserted even if the test fails. Existing application tables, plans, classifications
and workout logs are outside the test schema.

## Numerical examples checked

These examples are test fixtures, not edits to personal training records.

| Scenario | Expected and verified target |
| --- | --- |
| Normal session, range 6–10, previous 60 kg × 10/10/9, adequate RIR | 60 kg × 10/10/10 |
| Two complete ordinary executions at 60 kg × 10/10/10, adequate RIR, 2.5 kg step | 62.5 kg, 3 × 6, original target RIR |
| Final week of a configured block, reference 60 kg, 3 × 6–10, RIR 2 | 52.5 kg, 2 × 6, target RIR 4 |
| First normal exposure in the following cycle | Return to 60 kg, 3 × 6–10; old confirmations do not produce an immediate increase |
| Approved Machine Chest Press alternative, its own 60 kg history and 5 kg step | 65 kg, 3 × 6; no original-exercise weight step is reused |
| Deload log with two sets | Reduced expected coverage, no misleading progress/regression delta |
| Missing labels/RIR, incompatible history or unsupported equipment step | Explain the missing evidence or manual decision; do not invent a load |

The live check also covered the initial **More data needed** state in a new block.
Numeric recommendations require linked, comparable working sets and recorded RIR;
publishing the update does not manufacture this evidence or classify old sets.

## Automated verification

`.github/workflows/tests.yml` runs on pushes to `main`, pull requests and manual
dispatch. It installs the project requirements on Python 3.12, starts a disposable
PostgreSQL 16 service, runs the entire 235-case suite and compiles application
modules. The workflow uses test credentials only and does not receive the live
database URL. Its run is the ongoing publication check; this document records
the verification performed for the update rather than guaranteeing future runs.

## Scope and limits

- The calendar contains recorded history and plan/session assignments; Analytics
  contains the derived targets and observed plan comparisons.
- Recommendations are read-only. Selecting an alternative in the preview neither
  edits the plan nor approves a future replacement.
- The final week of each repeating 6-, 7- or 8-week block is deload. The schedule
  does not diagnose fatigue or prove recovery.
- Timed progression, bodyweight-to-loaded transitions and assistance-machine load
  selection require manual decisions where the engine cannot support a target.
- Overall strength and fatigue remain descriptive metrics that include logged
  deload work; deload-specific comparison handling applies to Plan execution.
- This release does not add authentication, multiple-user data isolation or a
  full bootstrap of the legacy production schema.
