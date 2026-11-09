# Final cleanup validation: 9 November 2026

Stage 9 completes the cleanup acceptance checks. The application passed the
semantic comparisons, automated suite, dependency/static checks and desktop/mobile
browser journeys described below. This stage adds verification evidence and
documentation links; application rules and stored user data remain unchanged.

Application under test: **`4319cbf`**. The measurement checkout was clean.
The [stage 9 artifact](../baselines/stage-9.json) contains individual timing
samples, query counts, environment versions and verification results.
Use the [documentation index](../README.md) for maintained behavior and commands.
This report is a dated snapshot of the stated application commit.

## Acceptance results

| Check | Result |
| --- | --- |
| Full local suite, Python 3.12.2 | **566 passed, 6 skipped**, no failures or errors |
| Exact-source CI, Python 3.11 and 3.12 | **572 passed on each version**, including all six PostgreSQL cases |
| Dependency consistency, Ruff lint and format | Passed; all **159 tracked Python files** use the shared format |
| Python 3.11 syntax and application/tooling compilation | Passed |
| Frozen synthetic calculations | All seven semantic sections and reviewable examples match the pre-optimization reference |
| Rendered output comparisons | Nine route-output hashes on each dataset match stage 7; unchanged cold/warm outputs within each case |
| Query-count comparison with stage 7 | Warm median counts match in all twenty dataset/case combinations |
| Application database integrity | All **20 inspected tables** match before/after acceptance; **2531 recorded sets** retained |
| Migration preview | No pending revisions; migrations were not applied during live acceptance |
| Local desktop/mobile browser | Fourteen check groups passed, no Streamlit exceptions or JavaScript errors |
| Public desktop/mobile browser | The same fourteen groups passed against the normal Cloud URL and embedded app |
| Local Markdown references | File/image targets, heading anchors and code-fence structure passed; counts are in the artifact |

The exact-source [GitHub Actions run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/42642710509)
uses disposable PostgreSQL 16. Locally, `TEST_POSTGRES_URL` is unconfigured,
so the six database cases are skipped. The application database is used only
for guarded reads; it is not substituted for the integration-test database.
The final report commit runs the same CI workflow after publication.

## Functional coverage

The full suite exercises writes against isolated fixtures. Real-browser journeys
use the running application with existing data and avoid submitting writes.

| Scenario | Automated coverage and browser evidence |
| --- | --- |
| Create/revise plans and preserve history | Plan storage/view, navigation and lineage tests; browser checks one exercise form and an unsaved workout-name draft across page navigation |
| Starting loads after plan/context changes | History-starting-load, manual-start, lineage and recommendation tests retain exact-exercise fallback, remembered choices and linked progression evidence |
| Pull-ups, dips, assistance and timed work | Load, bodyweight-entry and recommendation cases preserve confirmed legacy body mass, explicit load components, seconds and missing RIR |
| Workout entry and TXT import | Parser, data-manager and entry tests verify saves, rollback, warm-ups and load snapshots; browser opens TXT import and manual entry, then closes without saving |
| Session links, moved workouts and replacements | Schedule, adherence, performance and PostgreSQL cases cover assignments, actual dates and explicit replacements |
| Progression, failures, mixed loads, deload and return | Progression/rule/history/deload cases plus frozen semantic examples; browser switches upcoming workouts and opens target explanations |
| Historical filtering and active plan | Navigation/analysis tests and browser confirm a historical period does not change the upcoming workout |
| Cache refresh and architectural boundaries | Data-loader, data-manager, read-cache and architecture cases cover successful writes, rollback, scoped reads and independent contexts |

The previously corrected workout scheduled for **6 November**, performed on
**7 November**, still reports **Completed: 18/18 sets** through the active
adherence reader. This check does not infer another replacement or edit a plan.

## Performance comparison

The same runner and timing definitions as the [original baseline](performance-baseline.md#measurement-method)
were used: the actual Streamlit entry point, one cache-cold render and three
warm samples per route. Upcoming-workout switching has three warm interaction
samples. Tests, synthetic measurements, PostgreSQL measurements and browser
journeys ran sequentially. Analysis uses **All time**.

Existing PostgreSQL workload; times below are warm median **seconds**, and
query columns show the observed warm SQL-count range:

| Route or interaction | Stage 3 time | Final time | Stage 3 SQL | Final SQL |
| --- | ---: | ---: | ---: | ---: |
| Overview | 7.923 | 2.713 | 128 | 28 |
| Plan exercise analysis | 4.167 | 2.173 | 70 | 23–24 |
| Recorded exercise analysis | 0.087 | 0.089 | 0 | 0 |
| Plan consistency | 4.211 | 2.097 | 70–71 | 23 |
| Muscle map | 1.155 | 1.141 | 15 | 12 |
| Set allocation | 1.158 | 1.053 | 15 | 12 |
| Body measurements | 0.029 | 0.029 | 0 | 0 |
| Plan | 2.621 | 0.907 | 45 | 11 |
| History | 3.807 | 2.110 | 61 | 22 |
| Change upcoming workout | 7.485 | 2.742 | 128 | 28 |

Overview uses **78.1% fewer SQL statements**, with a warm median render time
**65.8% shorter** in these captures. The query reductions established during
the data/cache work remain present after restructuring, retirement and tooling
changes. Routes already served without SQL stay at zero warm statements.

One final plan-exercise sample executed 24 statements, while the other two
executed 23. Its median count remains 23, matching stage 7. All samples are
retained in the artifact rather than treating every rerun as an identical count.

The artifact also retains synthetic timings and six direct calculation timings
on preloaded input. These local server-side observations include serialization,
database round trips and instrumentation. They exclude browser paint and are
not a production latency guarantee. With three warm samples, small timing
differences on already fast views do not establish an algorithmic regression.

## Data and comparison boundaries

The synthetic fixture and all seven semantic hashes are unchanged from stage 3.
The live dataset has one intentional difference from stage 3: stage 4 saved
the user-confirmed exercise replacement, taking `training_plan_exercise_matches`
from three rows to four. The [stage 4 report](data-access-optimization.md#validation)
records that correction. Recorded sets were not rewritten.

Live displayed-output equality is checked against the corrected stage 7 dataset.
Its table counts and all nine output hashes match. Both benchmark datasets have
matching before/after fingerprints, and an additional live fingerprint bracketed
the live benchmark and browser acceptance. Read-only transaction guards and SQL
write rejection protected the local browser instance and live benchmark.

No migrations, seeds, session assignments, load confirmations or production
workout writes were performed during this acceptance stage. The six PostgreSQL
integration tests apply migrations and write synthetic records inside disposable
schemas, then roll back and assert cleanup.

## Browser scope and remaining limits

Chrome **157.0.8103.38** ran headlessly at **1440 × 1000** and **390 × 1000**.
All four pages, both exercise-analysis scopes, plan consistency, both muscle
views and body measurements were exercised. Checks include keyboard workout
selection, explanations, draft persistence, import/manual-entry opening and
closing, stacked mobile Overview columns, editor-button alignment and absence
of horizontal overflow. Captured screenshots were visually inspected.

The same journeys passed on the [public application](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).
Its runtime commit SHA is not exposed, so the public result attests to the
visible deployment behavior. Exact-source measurements and test evidence refer
to `4319cbf`. Browser screenshots remain local acceptance artifacts; the
[documented screenshot gallery](../user-guide.md#screenshots) retains its original
5 November capture date.

Physical devices, Safari/Firefox and a dev-container launch are outside these
checks. Existing SQLite date-adapter warnings and the Streamlit
`st.components.v1.html` deprecation notice remain follow-up maintenance items;
they did not fail the checks. Direct dependencies are pinned, while transitive
dependencies still follow their upstream ranges.

The product remains a public single-user demo. A complete database bootstrap,
anonymized deployable sample data, Docker Compose and authentication/data
isolation remain planned work, as described in the [project README](../../README.md#scope-and-next-work).
This cleanup preserves those scope limits and completes all nine stages.
