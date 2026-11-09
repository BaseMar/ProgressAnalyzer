# Legacy code retirement

> Historical record: describes its stated release or cleanup stage. For maintained guidance, start at the [documentation index](../README.md).

Stage 6 removes the unused implementation groups identified in the
[inventory](project-inventory.md), after the active date utility and recorded
history readers were separated in [stage 5](project-structure.md).
Recommendation rules, applied migrations, recorded user data and active
navigation remain unchanged.

## Removed implementation groups

| Group | Removed modules or branches | Existing replacement |
| --- | --- | --- |
| Aggregate metrics engine | `metrics/metrics_engine.py`, `metrics/registry.py` | Routes call the calculations needed for the selected question |
| Legacy aggregate summaries | `metrics/body_metrics.py`, `fatigue_metrics.py`, `frequency_metrics.py`, `progress_metrics.py`, `session_metrics.py`, `set_metrics.py` | Recorded exercise metrics, plan performance/insights and measurement timelines |
| Legacy input assembly | `metrics/input_builder.py` | `data_loader` assembles domain input through `mapper` |
| Legacy frequency calendar utility | `metrics/utils/calendar.py` | Retired with its exclusive aggregate-frequency consumers; active calendar/schedule logic is separate |
| Exercise comparison screen | The unused library selector, legacy KPIs, dual trends and ranking table; `ui/utils/exercise_table.py`, `ui/utils/muscle_tags.py` | One recorded exercise, performance/workload selection, load-aware charts and source sets |
| Body-summary screen | Snapshot, recomposition/proportion recommendations, generated insights and their exclusive trend/KPI helpers | Selected recorded measurement, source dates and History measurement-entry forms |
| Duplicate calendar plan picker | `PlanScheduleView.render_picker`, `HistoryView._render_history(use_existing_plan=...)` | Public History rendering uses the shared active-plan selection and optional plan overlay |
| Unused small helpers | `SidebarUpload._parse_set_tokens`, `ui_helpers.DANGER` | The active TXT token parser and existing UI colors remain |
| Unused facade methods | `DataManager.load_normal_workout_recommendations`, `DataManager.load_training_plan_version` | Existing database/service APIs remain available where used |

The two active analysis views now have one `render()` path. Exercise analysis
no longer accepts an unused raw-set DataFrame. Its actual set records still
come from the prepared exercise metrics. Body metric configuration no longer
carries the unused minimum/maximum ranking options of the retired screen.
The active parser's duration/repetition regex helpers and legacy Polish TXT
labels are preserved.

All twelve removed application modules were checked for application, CLI,
test, package-export and literal AppTest-script references. The old module
names were also removed from `metrics.__all__`. The existing heatmap assets,
global CSS, clipboard component, database drivers and administrative commands
are outside this retirement group and remain in use.

## Tests retained through active entry points

Assertions about the retired aggregate response are replaced with checks of
the active result that owns the same rule:

| Rule or workflow | Retained coverage |
| --- | --- |
| Body mass, assistance and missing total load | `test_load_analysis.py`: `compute_exercise_metrics`, plan performance, insights and recommendation functions |
| Explicit and inferred warm-ups; unknown RIR | `test_analytics_quality.py`, `test_set_interpretation.py`: recorded metrics plus the existing classification and plan workflows |
| Deload exclusion from performance with logged workload preserved | Recorded exercise metrics and plan-specific deload cases |
| Same-day sessions, start-time ordering and independent set order | `test_session_comparisons.py`: dated recorded series and per-session results |
| Timed performance and changing load conventions | Recorded metrics, load-aware charts and strict plan comparisons |
| Storage-row/domain conversion | `test_data_loader.py` replaces the legacy builder fixture with the real loader and an isolated synthetic database; row-specific mapper tests remain |
| Session links, moved workouts, future/empty months and exercise replacements | Calendar and adherence tests now use `HistoryView.render()`, matching the application's public route |
| Measurement dates and active UI controls | Existing KPI, navigation, chart and measurement-entry tests |

Twelve aggregate-specific test functions are retired: eight for the old engine
and summary response, three for old frequency/window summaries and one for the
retired fatigue score. Their absence is an intentional API retirement, not a
test failure. The builder test is replaced one-for-one by the active-loader
case. Session-date/start-time fields remain covered without recreating the
retired session-duration summary. New code should not reintroduce that engine
just to preserve its former test shape.

## Remaining compatibility

`db.progression` is intentionally retained as the documented import path for
the application recommendation entry points. The normal-date wrapper still
rejects deload dates. Immutable-version lookup remains in `db.training_plans`;
only its unused `DataManager` wrapper was removed. Existing table imports used
by isolated fixtures remain available from `db.plan_adherence`, with canonical
ownership in `db.recorded_workouts`.

There is now one non-CLI module outside the application import closure:
`db.progression`. The inventory treats it as a review item; it is a deliberate
compatibility facade rather than a deletion candidate. All other reviewed
out-of-graph legacy modules have been retired.

## Verification and scope

The updated inventory contains **110 application modules**, down from 122.
Application source falls from **11,265 to 9,681 lines**, including comments and
blank lines: a net reduction of **1,584 lines (14.1%)**. There are 45 test files
and four tooling files. The application reaches 106 modules; three more belong
to administrative entry points. Reproduce the current inventory with:

```powershell
python scripts/project_inventory.py
python scripts/project_inventory.py --json
```

The full local suite reports **566 passed, 6 skipped**. The six isolated
PostgreSQL write/migration cases require `TEST_POSTGRES_URL`, which is not
configured locally. Compilation covers the application, service and tooling
modules. No new dependencies or migrations are required.

The [stage 6 verification artifact](../baselines/stage-6.json) records the final
render samples, query counts, semantic comparisons and database-integrity
checks against stage 5. The synthetic semantic fixture remains unchanged.
All seven semantic sections, nine captured route-output hashes on each dataset
and warm SQL counts in twenty cases match stage 5. Both captures preserved
every inspected application table, including all 2531 existing recorded sets.
These checks use the same AppTest and SQL timing definitions as the
[original baseline](performance-baseline.md); they do not measure browser paint.

This stage removes obsolete implementations. It does not claim a new
algorithmic speed improvement. Dependency separation, formatting/static tools
and documentation consolidation remain later stages of the cleanup.
