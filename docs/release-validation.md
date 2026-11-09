# Analytics redesign: release verification

Historical release report. Results below belong to the stated release; current
recommendation behavior is documented in the
[progression rules](progression-redesign-rules.md).

Verification date: **5 November 2026**. Verification and publication are complete.
Application release: `6636442`; fresh Cloud rebuild: `63051e4`.
Target: [existing Streamlit Cloud app](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app),
deployed from `main`. Streamlit is pinned to **1.66.1**.

## Verification results

| Check | Result |
| --- | --- |
| Full suite on Python 3.12.2 / Streamlit 1.66.1 | 316 passed, including five PostgreSQL cases |
| Production migration preview | No pending migrations; revisions 001-005 are already applied |
| Navigation on configured PostgreSQL data | Overview, Analysis, Plan and History passed |
| Analysis questions | Exercise progress, plan consistency, muscle distribution and body measurements passed |
| Input ownership | Calendar, assignment, replacements, set corrections and import live in History |
| Draft persistence | Exercise/workout switches and leaving/returning to Plan preserve unsaved values |
| Dates and low-data behavior | Mixed dates, moved/early workouts, first measurements, missing RIR and partial logs verified |
| Desktop browser, 1440 px | All pages and all four analysis questions passed |
| Mobile browser, 390 px | Overview stacks; editor controls remain compact; calendar has no horizontal overflow |
| Dropdowns and alternatives | Native selectors work; substitutes retain their own history and equipment step |
| Compilation and whitespace | Passed |
| GitHub Actions for application commit 6636442 | Passed: [workflow run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/41952747874) |
| GitHub Actions for rebuild commit 63051e4 | Passed: [workflow run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/41953847919) |
| Published Streamlit Cloud app | All four pages and Analysis questions passed after rebuild; no application exceptions |
| Public URL and embedded app frame | Loaded successfully through the normal Cloud wrapper |
| Live dropdown styling and keyboard | Teal option text/selection; End, Home and Escape interaction passed |

The browser journeys opened and closed import, previewed a plan revision and
selected analytical questions. They did not save a workout, plan, classification,
replacement or body measurement to the demonstration database. Screenshots in
`screenshots/` were refreshed from the pinned local application and demo data.

The full suite ran with an explicit `TEST_POSTGRES_URL` supplied only inside the
test process. Each PostgreSQL case creates a unique schema inside a transaction,
defines synthetic legacy tables, applies migrations 001-005 and rolls back the
schema and fixture records. Removal is asserted even if a test fails. Existing
application tables and logs remain outside those schemas.

## Decisions reproduced from fixtures

| Scenario | Verified result |
| --- | --- |
| Normal 6-10 range; previous 60 kg x 10/10/9 with adequate reserve | Next target 60 kg x 10/10/10 |
| Two complete 60 kg x 10/10/10 executions with reserve and a 2.5 kg step | Next target 62.5 kg, 3 x 6 |
| Scheduled deload; reference 60 kg, 3 x 6-10, RIR 2 | 52.5 kg, 2 x 6, target RIR 4 |
| First normal exposure after deload | Resume 60 kg, 3 x 6-10; no immediate increase from old confirmations |
| Approved alternative with its own 60 kg history and 5 kg equipment step | 65 kg, 3 x 6; the original exercise step is not reused |
| More reps at equal per-set load and RIR | Observable output increase, with source sessions/sets retained |
| Heavier load with fewer reps, or changed per-set RIR | Context note, without an automatic regression/progress verdict |
| Latest linked execution is incomplete, empty or lacks RIR | Evidence barrier; no fallback to an older successful result |
| Deload with two prescribed sets | Reduced expected coverage; no ordinary regression delta |
| Timed exercise without RIR | Duration remains usable; unsupported automatic timed increases are not invented |
| One body measurement, without composition records | Recorded value is shown; no unsupported trend label |

## Publication procedure

The repository's Tests workflow runs on pushes to `main`. It installs requirements
on Python 3.12, starts disposable PostgreSQL 16 and runs the full suite plus
compilation. It uses disposable service credentials and receives no application
database secret. After pushing this candidate, verify its exact workflow SHA and
repeat the read-only browser journey against the Cloud URL.

That journey passed against both the deployed app frame and the normal public
URL after the rebuild. It covered all four pages, each Analysis question, import
opening/closing, the single-exercise editor and 390 px mobile layout. No demo
records were saved or corrected during acceptance. The final documentation commit
records these results and does not change application behavior.

The first Cloud check exposed a mixed in-memory revision: the new entrypoint
used an old six-page sidebar module and an old set-correction function. This
caused a History error despite a healthy server. The deployment release marker in
`requirements.txt` triggered a fresh Cloud environment build and resolved the
mixed revision; dependency versions are unchanged. [Community Cloud detects changes to the dependency manifest and
redeploys](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app).
For future releases that move modules, refresh that marker or reboot the app
from its management page rather than relying on the previous interpreter state.

## Scope and limits

- Overview contains current decisions and the only next-workout preview.
- Analysis renders one question at a time with its own historical period.
- Plan appends immutable revisions; History owns source input and corrections.
- The active plan is shared; a historical filter never changes future targets.
- RIR thresholds, the 21-day evidence limit and repeating 6/7/8-week deload schedule
  are explicit application rules. They do not measure technique, muscle growth,
  physiological fatigue, recovery or overall training effectiveness.
- Numeric preview targets do not edit plans or logs. A preview alternative does
  not approve a future replacement.
- Timed progression, assistance-machine loads and transitions to external load
  still require manual decisions where evidence cannot support a target.
- The deployment remains a public single-user demo; this release adds no
  authentication, data isolation or complete legacy-schema bootstrap.
