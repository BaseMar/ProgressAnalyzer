# Workout Progress Analyzer

An end-to-end analytics dashboard for recorded training progress, plan consistency,
next-workout targets, muscle exposure and body measurements.

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
a user's recorded performance is changing, whether logs match the plan, or how
training is distributed across muscle groups.

This project turns raw workout and body-measurement data into an analytical
dashboard that helps identify:

- comparable changes in exercise performance,
- training consistency,
- recorded effort and evidence gaps,
- body-part volume distribution,
- body-measurement trends.

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

The deployed version uses personal training and body-measurement data
prepared for demonstration purposes and stored in a hosted Supabase database.
Local development uses the same application code, but requires a
PostgreSQL-compatible database configured through `DATABASE_URL`.

This is a public single-user demo, not a multi-user product with private
per-user data isolation.

## Project Status

The application is functional and deployed as a public single-user demo. Core
analytics, versioned plans, progression/deload targets, TXT import and database
integration are implemented. Four task-oriented pages separate decisions,
analysis, planning and source history. GitHub Actions runs tests with disposable
PostgreSQL. Planned infrastructure work includes a complete database bootstrap,
anonymized seed data and Docker Compose.

## Preview

![Current training decisions and next workout](screenshots/Overview.png)

![One exercise analysed in its plan context](screenshots/Analysis_Exercise.png)

![Recorded calendar and session history](screenshots/History.png)

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

Workout Progress Analyzer is a Streamlit dashboard for tracking recorded training,
plan consistency, exercise trends, body measurements and body composition.
It imports workout data from a database, maps it into a small
domain model, computes core metrics in a separate calculation layer, and renders
the results as focused dashboard views.

The app is built for lifters who want more than a list of completed workouts.
It highlights whether performance is moving up or down, whether volume is
distributed sensibly across body parts, and whether body composition is changing
alongside training.

## Example Insights

The dashboard can answer questions such as:

- Did I record more reps at the same load and RIR in the same workout context?
- What does the next workout prescribe, and which sessions support that target?
- Which muscle groups receive the most weekly volume, and which may be
  undertrained?
- Which exercises had less reserve than planned, or need more evidence before
  assigning a new target?
- Are high-volume sessions concentrated in specific periods or body parts?
- Is body weight changing together with muscle mass, fat mass, or body fat
  percentage?
- Are body measurements and proportions moving in the expected direction over
  time?

## Features

### Training Analytics

- Evidence-backed observations and next-workout targets in Overview.
- Exercise comparisons within saved plan targets, or one recorded exercise's
  eligible performance/workload series at a time.
- Plan consistency: linked workouts, set coverage, range checks and weekly history.
- Local historical periods in Analysis; future recommendations use their own dates.

Per-exercise workload retains light and unknown-effort work. Ordinary performance
uses eligible working sets; planned deloads are excluded. Timed exercises use
seconds without requiring RIR. Substitutes retain separate exercise identities.
The former overall strength rankings and unvalidated fatigue-score screens are
not exposed in the four-page navigation. Backend calculations remain available
for compatibility; the interface does not present them as training effectiveness.

### Body-Part Analysis

- Weekly set volume by body part.
- Muscle-group exposure through exercise-to-muscle mappings.
- Volume distribution across trained body parts.
- Heatmap against editable target volume ranges.

### Body Metrics

- Body weight, muscle mass, fat mass, water mass, and body fat percentage.
- Measurement trends for chest, waist, abdomen, hips, thigh, calf, and biceps.
- One selected measurement with source dates and an observed change.
- First observations and measurement-only dates remain visible; direction alone
  is not labelled improvement or deterioration.

### Data Import

- TXT workout import in History, opened by Add workout.
- Flexible parsing for common set, RIR, and time-range formats.
- Exercise matching for imported exercise names.
- Option to add missing exercises with inferred muscle targets.

## App Sections

- **Overview** ? one conclusion, at most three annotations and the only
  next-workout recommendation. Uses recent actual dates, independently of filters.
- **Analysis** ? choose Exercise progress, Plan consistency, Muscle distribution
  or Body measurements. Only the selected question is rendered. Choose the month
  here; source details stay collapsed until needed. Unplanned exercises remain
  available via All recorded exercises.
- **Plan** ? weekly summary, block settings and versioned routine. Edit one
  workout and one exercise at a time. Draft values survive switching items/pages.
- **History** ? calendar, recorded sets, explicit plan assignments, session-specific
  replacements and optional set corrections. Add workout opens TXT import here;
  the sidebar button is a shortcut. Add body measurement opens the measurement
  forms here, including when no measurements exist yet.

One active plan is shared between these tasks. Overview and Plan have no history
month selector. Analysis and History retain their own date selections.

Muscle distribution calculates **Target** from one full reference week of the
active plan version effective today. Saving a new plan selects it automatically;
future versions take effect on their start date. The month filter affects logged
sets only. Saved muscle factors weight both planned and recorded sets (for
example, primary 1.0 and secondary 0.5). Timed sets count once, independent of
their duration. Deload prescriptions remain in Overview; this table describes
the base weekly routine.

**Min = 10, Max = 20 weekly sets** is a general hypertrophy reference, based on
[IUSCA (2021)](https://doi.org/10.47206/ijsc.v1i1.81) and
[ACSM (2026)](https://doi.org/10.1249/MSS.0000000000003897). This practical range
does not establish individual MEV/MRV or separate limits for every muscle.
Broad catalog groups (such as Legs), saved fractional allocations and timed
holds make the comparison approximate. Lower volumes can produce growth, and
20 is not a recovery ceiling. The target is never clamped to this range;
the table reports whether the plan is below, within or above it. Map colors
compare logged weekly sets with the plan, using a ±10% band. Without a plan,
colors use the reference range instead. Blank target means unavailable;
zero means the muscle is not allocated any sets in the plan. Missing mappings
or plan read errors leave targets blank instead of showing partial totals.
Manual heatmap range settings are no longer read or written.

History → Add workout supports **Import TXT** and **Enter exercise**. Manual
entry records reps or seconds, per-set weight, RIR and set purpose. For explicit
bodyweight logs, kg means additional weight; body mass and assistance are saved
separately. The latest body-mass measurement on/before the workout date is offered
as an editable suggestion. Missing body mass or unknown assistance remains unknown.

TXT import keeps its original kg convention by default. Open **Review body mass
and load types** to choose an explicit convention and inspect the total load
before importing. All exercises in an import are committed atomically. History
shows the saved load components, and **Body mass and load details** allows an
individual set to be corrected. Apply migration `006_set_loads` with
`python -m db.migrate --apply` before using explicit load entry. Existing
analytics/progression still use their previous load convention until the analysis
step in [the implementation plan](docs/bodyweight-implementation-plan.md).

## Training Plan editor

Open **Plan**, choose the active plan, or switch on **Create a new plan**.
Historical periods do not change the routine or block settings.

Saved plans open as weekly reference cards, with exercises available under
`Reference exercises`. Switch on `Edit as a new version` to change a saved plan.

1. Enter the plan name and effective date.
2. Add named workouts and choose their weekdays. Select one `Workout to edit`.
3. Add exercises from the catalog and select one **Exercise to edit**. Set its sets, minimum/maximum,
   and measurement unit. For example, 3 sets with 6–10 reps.
4. Use the arrow buttons to reorder exercises. Target RIR and the available weight
   step are in the collapsed `Progression & RIR` section of each exercise card.
5. Save the plan. All workout cards are saved together; editing an existing plan
   appends a version with a later start date. Previous versions remain available.

The plan editor requires migration 001 described below. Calendar assignments
require migration 002; execution analysis and confirmed replacements require
migration 003. Progression and deload recommendations are shown in
`Overview -> Next workout` and are also available through
the backend API.
Native tables and inputs use the shared dark/teal theme in `.streamlit/config.toml`.

### Progression configuration

Migration 005 adds versioned block settings. Under `Progression & training block`,
set the block start date and choose 6, 7 or 8 total weeks. The final week is reserved
for deload: for example, a 7-week block means 6 ordinary weeks followed by a deload
week. Blocks repeat automatically from the saved start date, so deload returns
every 6, 7 or 8 weeks. Weeks are seven-day intervals from that date, including
midweek starts. Missed workouts do not shift the calendar or prove fatigue.

The block start is separate from the plan version's effective date. Edits inherit
the existing start and length, so saving a revision does not restart the block.
An explicit change to either field is stored in the new snapshot; older snapshots
keep their configuration. Missing settings in revision API calls also preserve
the previous configuration. Existing plans remain unconfigured after migration
until the user explicitly enables `Configure training block` in the editor.

Each exercise keeps its own optional weight step in kg and target RIR. Use the
same weight convention as the workout log (including per-dumbbell weights if
applicable). Blank values remain unknown; a weight step must be finite and positive.

### Normal-session progression engine (step 2)

`DataManager.load_workout_recommendations(plan_id, day_id, scheduled_date,
as_of=...)` is the general entry point. It returns a `WorkoutRecommendation`
with block phase/cycle/week/dates and immutable per-exercise recommendations.
It reads linked history across month filters and does not write recommendations
to the database or change plan targets. No new migration is required.

`load_normal_workout_recommendations` remains a compatibility wrapper returning
only the exercise tuple; it rejects deload dates. The pure
`metrics.progression.recommend_normal_workout` remains the low-level normal-only
engine. Use `recommend_workout` or the general database API for arbitrary dates
so that deload classification and cycle boundaries cannot be bypassed.

Rules are deterministic and return `increase_reps`, `increase_weight`, `maintain`
or `insufficient_data`, plus per-set goals, target RIR, a reason code/explanation
and evidence session IDs/dates:

- Compare only the same exercise and workout context within the current cycle,
  using actual session chronology and excluding data recorded after `as_of`.
- Require complete working sets, recognized automatically or explicitly corrected,
  a target RIR and recorded RIR for repetition-based increases. Missing RIR does
  not support an increase; timed comparisons do not require repetition-based RIR.
- Treat target RIR as a minimum reserve in every set. Below-target reserve or reps
  below the lower bound keeps the logged load and original range.
- At one common working load and within the range, add one total rep to the
  lowest-repetition set (first set breaks ties), without exceeding the upper bound.
- At/above the upper bound, require two consecutive complete executions on different
  recorded days, at the same load, with enough reserve. Then add exactly one
  available weight step and target the lower repetition bound in every set.
- Missing evidence, changed contexts or a new block do not manufacture confirmations.
  A linked session with no matching work does not fall back to older successful work.
- Mixed per-set loads retain their individual loads/ranges; timed exercise progression
  and automatic transitions from zero-load/bodyweight to weighted work are not supported.

Default `ProgressionPolicy` uses two confirmations, a 21-day history-gap limit
and a 10% relative load-step cap. These are explicit, configurable application
guards, not validated individual training prescriptions. Large steps are held,
never replaced by an invented weight unavailable on the user's equipment.
Decimal arithmetic avoids values such as `12.299999999...` in suggested loads.

An old substitution approval does not automatically change the next workout's
exercise. Pass explicit `substitutions={plan_exercise_id: actual_exercise_id}`
to request a substitute; its own history is used. Its weight step must be supplied
separately with `replacement_weight_steps`, never copied from the original exercise.
The engine currently assumes ordinary positive resistance loads, not assistance
machines whose load direction has a different meaning.

The general idea is progressive adjustment of the training stimulus, discussed in
the [2026 ACSM overview](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/).
The exact one-rep rule, confirmation count, reset target and guards above are the
application's transparent policy, not an algorithm validated by that paper.

### Scheduled deload and return (step 3)

The general engine classifies the planned workout as `unconfigured`,
`not_started`, `normal` or `deload`. The final seven days of each configured
cycle use the following default `DeloadPolicy` for resistance exercises:

- Keep `ceil(planned sets * 0.5)` working sets, with at least one set. Three sets
  become two; four become two. A single-set exercise retains one set.
- Target the original lower repetition bound in every remaining set.
- Reduce each retained set's last normal load by at least 10%, subtracting whole
  available equipment steps from the logged load. Stop if the required reduction
  exceeds 20% or would make the load zero/negative; return `insufficient_data`
  with a reason rather than inventing a different step or available weight.
- Set the target reserve to `max(4, original target RIR + 2)`.

For example, a plan with 3 x 6-10, RIR 2, a 2.5 kg step and a complete normal
log of 60 kg x 10/10/10 gives **2 x 6 at 52.5 kg, target RIR 4** during deload.
The 7.5 kg reduction is three available steps (12.5%), not a fabricated 54 kg.
These are derived targets, not a guarantee of the RIR a user will achieve.

The latest comparable normal execution in the same cycle supplies evidence.
It must pass the same completeness, working-set classification, RIR and
21-day default history-gap checks as ordinary recommendations. Deload sessions
are never reused as a baseline, so multiple sessions in the deload week do not
compound the reduction. An explicit substitute uses its own history and supplied
weight step. Timed exercises, zero-load/bodyweight and assistance-machine load
selection are outside the automatic deload prescription; select loads manually.

On the first normal exposure after deload, use the last comparable normal loads
and original range from the immediately preceding cycle, without an increase.
This is `maintain` / `resume_after_deload`. It needs no weight step because it
does not change loads. Old upper-bound confirmations do not carry forward:
new-cycle executions establish progression again. Missing/partial latest evidence,
long gaps, a changed context or a manual change of block settings prevents reuse.
The calendar continues even if no deload session was logged; the rule does not
claim that the user recovered or completed a deload.

Historical plan versions retain their own block settings. Saving a revision with
the same settings preserves the schedule/history. A manually changed anchor or
length starts a separate recommendation history. A moved planned deload remains
deload; a normal slot actually performed during deload is also excluded from normal
baselines and confirmations. Results after `as_of` never supply evidence.

In **Analysis → Plan consistency / Exercise progress**, resistance-exercise deload dates use reduced
set counts and repetition/RIR targets for coverage and range checks. Their
comparisons are labelled deload and have no progress/regression delta; the next
normal execution compares against the previous normal execution. Amber diamonds
identify deload logs on the exercise chart, whose target band follows each date.
Raw history and saved plan versions are unchanged. Descriptive workload retains
logged deload work; the retired strength rankings and fatigue score are not shown.
The Next workout card presents these derived targets separately from historical
analysis, as described below.

The general reduction of training demand is supported as a design approach by
the [deload Delphi consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC10511399/).
It does not establish one optimal schedule or algorithm. The repeating 6-8 week
schedule, exact reductions, RIR targets and return rule above are explicit,
configurable application policy, not a physiological fatigue diagnosis or a
validated individual prescription. Analytics uses the default policy; alternative
policies are currently backend options and are not persisted as plan settings.

### Next workout card (step 4)

Open **Overview**, choose the active plan, and read **Next workout**
beside the recent observations. It defaults to the earliest
unlinked planned workout from today onwards. `Upcoming workout` lets you preview
other dates in the next four weeks; a future plan starts that window at its first
effective date. Slots on the same day remain distinct and follow their plan order.
The sidebar history month does not limit recommendations or their evidence.
Linked workouts disappear from this selector; overdue slots are not silently
rescheduled or treated as proof that a user skipped training.

The card shows the workout/date, normal or deload phase, block/week and deload
dates. Up to two available targets are shown by default, preferring changes.
**Full workout** opens every exercise, including maintained loads and entries
waiting for more evidence. Repeated missing-target reasons are grouped into a
single note instead of rendering empty cards for each exercise. Each exercise
has one compact target and decision: `Add a rep`,
`Increase load`, `Keep load`, `Deload`, or `Return after deload`. Uniform sets
are grouped, for example **62.5 kg · 3 x 6 reps · RIR >= 2**. Unequal reps and
loads retain their individual set targets instead of being averaged. Missing
evidence shows `More data needed` and the specific reason, such as incomplete
ordinary work, missing RIR or an unavailable weight step; no numeric load is
invented. Unsupported deload prescriptions are labelled `Manual target`.

`Why these targets?` contains the full engine explanation, evidence session
IDs/dates, and the default progression/deload rules. Historical source sessions
remain in History. Historical exercise comparisons and plan consistency are
separate questions in Analysis; neither repeats the upcoming recommendation. An unconfigured or not-yet-started block gets one
setup message rather than repeated empty recommendations for every exercise.

If an alternative was previously approved and logged in the same workout context,
`Use a confirmed alternative` lets the user explicitly choose it for this preview.
Its own history is used. Supply its available weight step in kg when required;
the original exercise's step is never reused. Choices are specific to the plan,
scheduled slot and date, so a choice for one workout does not silently carry into
the next. Alternative choices and steps are temporary UI state: they do not edit
the plan, save a session, or approve a future replacement. After logging the actual
session, confirm replacements through the existing data-correction controls.

No new schema or migration is needed. Recommendation failures are isolated from
the historical plan overview; the card never writes derived targets to logs.

## Planned workouts in the calendar

Open **History**. The calendar uses the same active plan as Overview; switch off
**Show planned workouts** to view recorded history alone. Its own month selector
lets you browse past and future dates. Each date uses the
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

Open **Analysis ? Plan consistency** and choose the active plan and analysis
period. The selected month refers to scheduled dates; sessions linked from other
dates/months are loaded in full. One short annotation reports linked workouts,
set coverage and logged sets within range. The weekly chart distinguishes full,
partial, unmatched and unlinked workouts. These are recorded facts, not proof of
training effectiveness. Exercise progress is a separate analytical question.

Summary ratios include only scheduled dates before today. Today's open workouts
and future slots neither lower nor inflate them. A moved workout counts as
recorded, but not on the planned day. Unlinked workouts are not proof of absence.
Timing, data quality and auditable source rows live under `Definitions & source
data`, rather than expanding the main overview.
Coverage excludes inferred/explicit warm-ups and uncorrected ordinary light or
low-effort sets, retains unknown-effort logs, and caps credit at
the planned count per position. Coverage alone does not indicate success against
the repetition/time range or RIR; these are checked separately below. Technique
and muscle growth are not assessed.

In **History**, select the planned day with a linked session and expand
**Confirm exercise replacements**. Choose the planned and actual exercises. For
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

Open **Analysis ? Exercise progress ? Plan targets**. Select one workout/exercise
context under `Exercise trends` to see its latest observation, range/RIR result and chart.
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
judgment that training was physiologically effective. Unknown effort remains
visible in descriptive coverage but cannot produce a progress delta. Timed
performance uses duration without requiring RIR.

## Decision annotations

In **Overview → What changed · what to do**, up to three
annotations show an observation, per-set evidence and a next action. The pure
`compute_training_insights` engine prioritizes less-than-planned reserve, deload,
increased output, lower output, changed effort, evidence gaps, changed load and
unchanged output, in that order. Ties prefer recent evidence. This is an explicit
display policy, not a training-effectiveness score.

Overview uses the last 28 **actual** days, independently of the history month.
This includes workouts performed early or moved from older planned dates.
Unlinked elapsed slots in that window are counted by their scheduled date.
Plan analysis continues to use the selected scheduled month.
Actual dates and session order choose the latest linked execution in each context; earlier history remains
available. Two complete ordinary executions on different days, at most 21 days
apart, support a paired observation. Changed target prescriptions, substitutes
and manually reset block settings have separate histories. An incomplete latest
execution is a barrier; the engine never falls back to an older successful log.

At equal per-set loads **and per-set recorded RIR**, changed total reps describe
changed output. A change in any set's RIR produces an effort-context note, even
when average RIR is identical. Changed load never automatically means regression.
Timed work compares seconds without requiring RIR. Less-than-planned reserve can
be reported from one complete execution. Deload uses reduced targets and is
excluded from ordinary comparisons. Missing RIR, incomplete sets, first baselines,
long gaps and unlinked elapsed workouts are grouped into one evidence message.
Missing linkage is never presented as proof of skipped training.

A numeric next action reuses the existing progression engine's actual selected
workout preview. It must cite the latest observed session and match exercise,
prescription and block settings. Current future targets are not attached to a
historical month. **Why?** contains the rule, evidence level (`paired`, `observed`
or `limited`), immutable source snapshots, dates, IDs, individual sets and inferred
classification provenance; attached recommendations retain their original reason
and evidence. No data is rewritten and no schema migration is required.

## Current training overview

Overview opens with a single conclusion based on the current block phase,
recent evidence and the actual selected workout's target availability. It does
not estimate physiological effectiveness. Below, the left column contains at
most three annotations; the right contains the only full next-workout preview.
The layout stacks below 920 px. Exact next-target numbers live in the workout
card; annotations point there instead of repeating the prescription.

The former five global KPI cards and two session charts are removed from the
landing page. Calendar, assignments, replacements, imports, session logs and
optional corrections now live in History. The active plan persists across all
four pages, with a safe fallback if that plan is no longer available.

The layout redesign continues in separately approved steps documented in
[analytics-redesign-plan.md](docs/analytics-redesign-plan.md).

## Working sets and warm-ups

Series are interpreted automatically in the metrics layer, without modifying
stored set values or writing inferred labels. Ordinary RIR 0–3 is working;
RIR 4–5 is light; RIR above 5 is low effort. A light set is a likely warm-up only
if it precedes the first known working set in the **same logged exercise** and
has a lower load. A later back-off set is not automatically a warm-up.

Light and low-effort work remain in descriptive workload, but do not establish
ordinary progression or fill planned working-set counts. Missing RIR stays
unknown: its logged work remains visible, while ordinary progress comparisons
and numeric increases require sufficient effort evidence. Timed work is evaluated
using duration and requires no repetition-based RIR. Linked planned deload work
uses the historical version's block settings, retains its lighter prescribed
sets, and never establishes an ordinary progression baseline. Month filtering
preserves this context, and global/exercise progress excludes deload exposures.

Explicit user corrections take priority over inferred purpose. `Working` can
override a light/low-effort interpretation, but it does not invent missing RIR.
`Warm-up` always excludes that set from analysis, including during deload.
These thresholds are application policy, not a diagnosis of a set's training
value. Derived results carry their kind, source and reason separately from the
original `is_warmup` value.

Migration 004 stores optional exceptions only. In History's recorded-session
details, open `Set interpretation · optional correction` and switch on `Correct a
set` only when needed. The editor shows the derived interpretation and its source.
`Auto` removes an explicit correction; `Working` and `Warm-up` save exceptions.
The former mandatory labelling control is removed from the analytical flow.
Calendar log totals still preserve recorded sets; explicit warm-ups carry a `WU`
badge. Training-visit frequency still counts recorded sessions. Source data are
cached for up to five minutes; imports and corrections invalidate the cache.

TXT import accepts explicit markers, including mixed markers on one line:

```text
1. Bench Press
Warm-up: 10x20 / 8x40
Working: 8x60 / 8x60
RIR: 4 / 3 / 2 / 1
```

`Rozgrzewka:` and `Robocze:` are also supported. Unmarked tokens retain an empty
stored label and are interpreted automatically at analysis time. Exceptions
remain stored separately from original set values; no new migration is needed.

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

For a bodyweight dead hang, record each hold separately as a duration:

```text
1. Dead hang
Working: 30s / 45s / 1:00
```

This example imports three working sets lasting 30, 45 and 60 seconds, with no
added weight. RIR may be omitted and stays unknown; seconds of reserve are not
repetitions in reserve. In Training Plan, choose `Measure = seconds` and the
desired time range. Timed sets use `duration_seconds`, contribute no tonnage or
estimated 1RM, and do not receive automatic timed progression recommendations.
The current TXT duration format does not capture additional hanging weight.

Wrist Curl and Reverse Wrist Curl use explicit forearm rules (wrist flexors and
wrist extensors, respectively), before the generic elbow-curl rule. Standard
straight-arm Dead hang uses forearm finger flexors/grip as primary, with shoulder
and scapular stabilization; biceps are not credited as a training target. These
are movement-based analytical labels and application role factors, not measured
muscle activation percentages. References:
[ACE wrist flexion](https://www.acefitness.org/resources/everyone/exercise-library/30/wrist-curl-flexion/),
[ACE wrist extension](https://www.acefitness.org/resources/everyone/exercise-library/29/wrist-curl-extension/),
[finger-hang/arm-lock-off study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10623130/).

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

Core rule: decision formulas live outside the UI. Database rows become
`MetricsInput` and immutable plan snapshots. Each view calls the pure calculator
needed for its selected task; the general metrics registry remains available
for backend consumers. Views may reshape or aggregate prepared values for a chart.

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
- `training_plan_progression` — block start and length for a configured plan
  version; no row means not configured.
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

Streamlit is pinned to **1.66.1** so local installs and Community Cloud use the
same widget renderer. After pulling a dependency change, reinstall requirements
inside the active project environment. Custom dropdown CSS supports both legacy
Base Web lists and current React Aria options; it preserves virtualized row sizes
and native scrolling. The plan editor numbers workout choices so that two unnamed
workouts remain distinguishable to the renderer.

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
`workout_sets`. Migration 005 adds versioned progression/block settings without
assigning defaults to legacy plans. These migrations do not change workout records.
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
boundaries, database constraints, and atomic rollback. Five additional integration
cases run against PostgreSQL when `TEST_POSTGRES_URL` is set. Each case creates a
unique schema, applies all five migrations, and rolls back its schema and synthetic
logs afterwards. They verify normal goals, deload/return, confirmed alternatives,
immutable versions and migration repeatability. They never fall back to the app's
`DATABASE_URL`.

```bash
python -m pytest
python -m compileall -q db metrics models ui streamlit_app.py data_loader.py data_manager.py mapper.py
```

For a PostgreSQL test database (PowerShell):

```powershell
$env:TEST_POSTGRES_URL = "postgresql+psycopg2://user:password@localhost:5432/progress_analyzer_test"
python -m pytest
```

The test role needs schema-creation permission. Without this variable, the five
PostgreSQL cases are skipped and the unit/SQLite/Streamlit tests still run.
The [Tests workflow](.github/workflows/tests.yml) runs the full suite with Python
3.12 and a disposable PostgreSQL 16 service on pushes to `main` and pull requests,
without application database secrets. The final update verification is recorded
in [release-validation.md](docs/release-validation.md).

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
- Extend the existing test pipeline with linting and more import-parser regression
  coverage.
- Extend the additive plan migrations into a complete legacy database bootstrap.
- Extend analytics with prediction-oriented features, such as estimated progress
  trajectory or fatigue-risk signals.
- Add user authentication and data isolation before treating the app as a
  multi-user product.
- Continue improving TXT import coverage for more free-form workout note styles.

## Screenshots

Captured 5 November 2026 using the pinned Streamlit version and configured demo
data. Browser verification is recorded in [release-validation.md](docs/release-validation.md).

### Overview

![Current conclusion, observations and next workout](screenshots/Overview.png)

### Analysis

![Exercise progress](screenshots/Analysis_Exercise.png)
![Plan consistency](screenshots/Analysis_Consistency.png)
![Muscle set allocation](screenshots/Analysis_Muscles.png)
![One body measurement](screenshots/Analysis_Body.png)

### Plan

![Weekly plan summary](screenshots/Plan.png)
![One exercise edited at a time](screenshots/Plan_Editor.png)

### History

![Calendar, assignments and recorded sessions](screenshots/History.png)
![On-demand TXT import](screenshots/History_Import.png)

### Mobile

![Stacked training overview](screenshots/Overview_Mobile.png)
![Compact exercise editor](screenshots/Plan_Editor_Mobile.png)
![Workout calendar and session logs](screenshots/History_Mobile.png)
