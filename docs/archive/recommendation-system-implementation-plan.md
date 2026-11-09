# Recommendation system implementation plan

> Historical record: describes its stated release or cleanup stage. For maintained guidance, start at the [documentation index](../README.md).

Date: 8 November 2026. Status: all eight stages completed and published.
Basis: the approved v1.0 progression rules at the time of implementation.
This document records the delivered scope and acceptance criteria for that release.
Verification details are in the [validation report](recommendation-system-validation.md).

Historical scope: the 9 November history-based starting-load update supersedes
this plan's manual-start policy. The [current rules](../progression-rules.md)
describe the active behavior. Original decisions and release results below are
retained as implementation history.

## Delivery status

| Stage | Status | Result |
| --- | --- | --- |
| 1. Rules | Complete | Approved equalization scheme; 10% / four executions / 21 days; full-set deload at 30-40%; timed work and manual bodyweight loads. |
| 2. Model | Complete | Versioned output, per-set goals and migration 007; hashes of six existing tables remained identical. |
| 3. History | Complete | Stable position keys, explicit inference provenance and detection of ambiguous recorded entries. |
| 4. Ordinary engine | Complete | One extra rep, equalization in equipment increments, one success and a new common load. |
| 5. Exceptions | Complete within agreed scope | Corrections, plateaus, long gaps, deload/return, timed work and manual load/assistance. |
| 6. Interface | Complete | Consistent goals, messages, sources and export; browser checks at 1440 px and 390 px. |
| 7. Plan and history | Complete | Approved version 6 (ID 15), effective 10 November, with 36 positions; comparison of 72 future decisions against recorded history. |
| 8. Publication | Complete | Release `a543c83` pushed to main; CI passed; rules and all four views verified in the public desktop/mobile application. |

Verification: 504 local tests and five separate PostgreSQL tests passed.
PostgreSQL used isolated schemas rolled back after each test. Compilation and
change checks passed. Browser checks covered all four pages, opening import and
the full workout, without JavaScript exceptions or horizontal Overview overflow
at 390 px. See the [validation report](recommendation-system-validation.md).

## Goal and scope

The system suggests the next workout for hypertrophy and strength. It handles
starting loads, load selection, fatigue-related reductions, per-set RIR and
unknown or varying rest intervals. Ordinary progression works without mandatory
block configuration. Targets remain suggestions, separate from saved plans and
actual results.

Order of work: rules, data model, history interpretation, ordinary engine,
exceptions, interface, plan configuration and historical evaluation, then publication.
Different per-set loads belong to the core scope rather than a post-release addition.

Each stage produces a concrete result, appropriate verification and a short
report covering what works, how it was checked and what remains. Tests accompany
behavior changes rather than being deferred until publication.

## 1. Finalize rules and decision examples

**Deliverable:** one specification and a case matrix with expected outcomes.

The user answered eight questions: **1B, 2A, 3B, 4A, 5A, 6B,
7 (existing notes), 8B**. At that release, these meant:

- increase only after every planned set succeeds at its own load;
- try one additional total repetition;
- require one complete success, without a second confirmation;
- prevent increases below target RIR, distinguishing the need for a reduction;
- correct the affected set after the first failure at the lower bound;
- let the user select an unestablished starting load with history visible;
- use existing warm-up and working-set labels;
- schedule deloads automatically from the calendar.

The user clarified mixed-load progression: first equalize lighter sets toward
the established first working load. For an 8-12 range,
`60 x 12 / 55 x 12 / 55 x 12` leads to `60 x 12 / 60 x 8 / 60 x 8`.
Only after all sets reach the ceiling at the common load should it rise by one
available increment, with the lower bound as every set's repetition target.

Additional decisions were closed: the 10% limit also applies to equalization;
a plateau requires four executions; a long gap exceeds 21 days; timed progression
adds five seconds; bodyweight load/assistance changes remain manual; and existing
set-purpose inference is retained explicitly. Deload retains all sets and reps,
reduces load by 30-40% and targets RIR 3-4. The following rules record the acceptance
scope of the delivered work.

- Separate confirmed user preferences from proposed parameter values.
- Tabulate progression from reps at existing loads, through equalization after
  complete success and reps at one common load, to a new common load. Include
  how earlier work affects later sets.
- Specify which set receives the additional rep and what happens after changing
  the first set.
- Finalize calibration, required RIR, below-minimum reps and load corrections.
- One success is sufficient. Specification v1.0 defines the four-execution,
  10% and 21-day thresholds and confirmation of RIR improvement.
- Distinguish warm-ups, working sets and load-selection trials during import;
  define behavior when purpose information is absent.
- Define automation for time, bodyweight, assistance and deload. Each variant
  needs a numeric rule or an explicit manual-calibration boundary.

**Acceptance:** each matrix case has an action, a goal or a reason for no goal,
and confirmation conditions. Before stage 4, no unresolved decision changes
ordinary progression. User-specific plan parameters may wait until stage 7;
the engine operates on each exercise's configuration.

## 2. Model recommendation configuration and output

**Deliverable:** models supporting the agreed rules and historical records.

- Separate recommendation policy from block and deload calendars.
- Preserve sets, range, RIR and real equipment increments; add only fields
  required by the agreed rules.
- Give exercise positions stable identities across plan revisions. Renaming a
  workout or changing its day must not by itself discard useful history.
- Separate set purpose from effort. Do not require new manual labels when the
  existing data already supports unambiguous interpretation.
- Include per-set goals, action, reason code, source sessions, confirmations,
  data limitations and rules version in recommendation output.
- Distinguish calibration, maintenance, an extra rep, equalization, a new common
  load, correction, deload/return and insufficient data.
- Add the next unused migration when necessary, retaining compatibility with
  older plans. Do not rewrite historical RIR or results.
- Treat roughly three minutes as a stated habit, not a historical rest value.
  Recording rest intervals remains optional.

**Main locations:** `models/progression.py`, `models/training_plan.py`,
`models/set_interpretation.py`, `models/workout_set.py`, `db/training_plans.py`,
`db/progression.py`, a new migration if needed, and `db/migrate.py`.

**Acceptance:** old and new configurations load correctly; round trips preserve
settings; migration leaves recorded results unchanged. Storage tests use fixture
data. Rollback planning accounts for older application versions rejecting an
unknown migration revision.

## 3. Share set interpretation and history selection

**Deliverable:** one set of observations for analysis and recommendations.

- Distinguish working sets, warm-ups, timed work and deload without using RIR
  alone to assign purpose. Preserve explicit corrections and their priority.
- Retain every set's position, load and RIR; do not average mixed loads.
- Distinguish recorded facts, a calibration hypothesis and a declared reason
  for a change.
- Under the original policy, separate history shown for manual starting-load
  selection from history eligible for progression from an established baseline.
  Do not generate a new starting-load candidate during manual calibration.
- Handle actual dates, moved sessions, plan revisions, repeated exercises and
  explicitly selected alternatives.
- A session without an unambiguous plan-position assignment does not confirm
  that position. Any baseline requires the same actual exercise.
- Do not skip a latest weak or incomplete execution to find an older success.
- Historical Analysis filters must not change future workout targets.

**Main locations:** `metrics/set_interpretation.py`, `metrics/plan_performance.py`,
`metrics/recommendation_history.py`, `metrics/load_metrics.py`,
`metrics/utils/set_values.py` and `db/plan_adherence.py`.

**Acceptance:** a set has consistent meaning in History, Analysis and engine
input. Comparisons use neither future results nor another exercise's kilograms.
Ambiguity is explicit and does not become a success or regression verdict.

## 4. Implement ordinary progression, including mixed loads

**Deliverable:** a deterministic ordinary-training engine matching stage 1.

- Under the original policy, show history when no baseline exists and let the
  user choose the unestablished start.
- Generate per-set goals for common loads and fatigue-related reductions.
- After mixed-load success, equalize lighter sets toward the established start.
  Retain targets at the reference load and reset raised sets to the lower bound.
- Increase the common load only after complete success at equal loads.
- Implement the additional rep, upper-bound confirmation and increase by an
  available equipment increment using the agreed unit of progression.
- Handle later targets after greater earlier-set work under the agreed rule;
  do not automatically require every set to improve at once.
- Explain the next action when an equipment increment is too large.
- Separate lack of readiness to increase from a need to reduce load. One RIR
  reading below target must not automatically lower the entire exercise's load.
- Support ordinary progression without a block calendar.

**Main locations:** `metrics/progression.py`, `models/progression.py`,
`db/progression.py`, `tests/test_progression.py` and `tests/test_recommendation_history.py`.

**Acceptance:** the ordinary-case matrix passes. Mixed loads do not produce a
generic unsupported result. Identical inputs, date and rules version produce
identical output, without changing the plan or history.

## 5. Handle failure, plateaus, deload and other variants

**Deliverable:** consistent behavior beyond an ordinary successful execution.

- Distinguish an unsuitable starting load from difficulties in later sets.
  Correct the first failure at the minimum; above it, first consider stopping
  earlier within the range.
- Assess possible plateaus from comparable work and reserve, rather than tonnage alone.
- Missing data and incomplete executions must not automatically imply regression.
- Apply the agreed baseline-reset mode after a history gap.
- Treat calendar-based deload as a separate mode. Resume an ordinary baseline
  afterward; a lighter week must not establish a new ordinary increase.
- Keep body mass, additional load and assistance separate. Less assistance
  increases difficulty. Do not assume future body mass.
- Use a separate progression unit for time, a clear side convention for
  unilateral work, and separate handling for special techniques.
- Use reported pain/injury only when actually available. Do not diagnose it
  from results or require a new mandatory questionnaire.

**Main locations:** `metrics/progression.py`, `metrics/training_block.py`,
`metrics/progress_metrics.py`, `metrics/training_insights.py`,
`tests/test_deload.py`, `tests/test_set_loads.py` and `tests/test_training_insights.py`.

**Acceptance:** each variant has an appropriate goal or an explicit agreed
automation boundary. Missing data does not invent loads; deload does not imply regression.

## 6. Connect the interface and shared messages

**Deliverable:** one consistent next action with its supporting evidence.

- Overview shows each set's load and target, RIR, the primary reason and access
  to the latest execution and confirmations.
- Plan configures exercise parameters and an independent deload schedule.
- History supports optional purpose and source-data corrections without requiring
  a manual explanation of every load change.
- Analysis distinguishes observations, comparison limitations and recommendations.
  Remove contradictory assessments from older rules.
- Workout-note export preserves mixed loads, per-set targets and space for actual
  results. Copying a target does not record an execution.
- All messages use shared engine output; views do not add independent rules for
  increasing or reducing load.
- Setting changes refresh calculations. Cache must not mix rules versions.

**Main locations:** `ui/next_workout_view.py`, `ui/overview_view.py`,
`ui/training_plan_view.py`, `ui/utils/plan_editor.py`, `ui/set_classification_view.py`,
`metrics/training_insights.py`, `metrics/overview_summary.py`,
`metrics/utils/recommendation_text.py` and `metrics/workout_template.py`.

**Acceptance:** the next-workout card, analysis and export agree without requiring
users to read technical reason codes. Plan to History to Overview navigation and
mobile layout work with complete history and missing data.

## 7. Configure the user's plan and verify historical decisions

**Deliverable:** proposed exercise configuration and a sample recommendation report.

- Read the active plan and history. Prepare per-exercise sets, range, target RIR,
  equipment increment and reference rest for hypertrophy and strength.
- For established baselines, show the latest relevant loads. For an unestablished
  start, the original decision 6B required visible history and manual selection.
  Distinguish this from increasing an already established baseline.
- Present configuration before saving it. Saving is a separate action that
  creates a revision without changing historical executions.
- Replay selected cases with the new engine using only results and settings
  available at the replay cutoff.
- Compare old and new actions, sources, confirmations and reasons. Significant
  differences must follow a specific new rule.
- Check the revised plan separately as future configuration. Do not present new
  range/RIR settings as historically applicable prescriptions.
- Check the full suite, storage integration on test data and interface journeys.
  Add tests for newly exposed cases or defects.

**Acceptance:** no unexplained decisions or conflicting screens remain. Document
selected cases, outputs, explanations and proposed settings. Historical replay
checks rule consistency; it does not prove future training effectiveness.

## 8. Publish and retire the previous mechanism

**Deliverable:** one active release with reproducible decisions.

- Before switching, identify the target commit, migration state and compatible
  rollback procedure that preserves new data.
- Retain old code for comparison if needed, but after switching, all screens
  must use the same active rules version and configuration.
- Publish after required tests and review of stage 7. Technical publication is
  a separate action from preparing this plan.
- Verify the running release, next-workout date, per-set targets, export,
  refresh after setting changes and existing-plan compatibility.
- Update README and release documentation. Do not present a previous release's
  report as validation of the new system.

**Acceptance:** the verified release runs; one engine supplies targets and
messages. Preserve historical records and a compatible rollback procedure.
Behavior after actual future training is a later observation rather than a
condition of technical implementation completion.

## Minimum case matrix for stage 1

| Case | Required specification decision |
| --- | --- |
| No exercise history | Calibration without inventing a load. |
| Lighter opening sets followed by heavier sets | Set purpose and manual starting-load selection under the original policy. |
| Constant load, result within range | Exact selection of the one-rep target. |
| First complete upper-bound result | Readiness to increase after one complete success. |
| Mixed loads such as 60/60/55 | Equalization after complete success; lower-bound reps only in raised sets. |
| 60 x 12 / 55 x 12 / 55 x 12 | 60 x 12 / 60 x 8 / 60 x 8 with sufficient RIR. |
| 60 x 12 / 60 x 8 / 60 x 8 | 60 x 12 / 60 x 9 / 60 x 8 with sufficient RIR. |
| Upper bound in all sets at a common load | Next common load and lower-bound reps in every set. |
| More work in the first set | Comparability and targets for later sets. |
| One RIR reading below target | Maintenance without automatic reduction. |
| Insufficient reserve at high reps | Stop earlier within the range. |
| Insufficient reserve at the minimum | Conditions and scope of load reduction. |
| Only later sets are weaker | Separate their correction from the starting load. |
| Missing RIR, missing sets or invalid records | Distinct limitations without false success/regression. |
| Explicit warm-up with low RIR or working set with high RIR | Purpose independent of effort. |
| Extra sets or ambiguous import | Select planned sets without double counting. |
| Variable or unknown rest | Limit inference without blocking the entire system. |
| Excessive equipment increment | A next action beyond indefinite maintenance. |
| Plateau or one changed RIR reading | Exact trend-confirmation requirements. |
| Long gap or return after deload | Re-establish the baseline and confirmations. |
| Changed name, day, order, range or RIR | Which history supplies a baseline versus an increase confirmation. |
| Alternative, different equipment or repeated exercise position | Separate identities and equipment increments. |
| Time, bodyweight, assistance or sides | Their own units, progression direction and automation limits. |
| Moved workout, duplicate session or future data | Chronology without duplicate/future confirmations. |
| Analysis filter, export or another screen | The same future target from the same engine. |

## Scope boundaries

The system does not automatically design a new exercise routine, add sets for a
plateau or diagnose overtraining, technique or health from logs. It does not
require a daily questionnaire, measurement of every rest interval or relabelling
all history. Extensions beyond the agreed scope need explicit rules before coding.
