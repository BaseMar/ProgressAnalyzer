# Analytics-first layout proposal

Status: approved, 5 November 2026. Steps 1–4 are implemented and verified.
Step 5 is approved and in progress. The user requires explicit approval
before moving from each completed step to the next.

## Product goal

The application should answer three questions: what changed, what requires
attention, and what to do at the next workout. Keep the existing visual theme;
change screen hierarchy, information density and the way results are explained.
Every default-screen item must support a training decision or explain evidence
quality. Keep source rows available on demand.

## Navigation and ownership

- **Overview:** current conclusion, at most three actionable annotations, and the
  next workout. This is the only home of the full next-workout recommendation.
- **Analysis:** exercise trends, muscle-group distribution and body measurements.
  Open one analytical question at a time instead of rendering all charts/tables.
- **Plan:** weekly routine and block settings, with one workout/exercise edited
  at a time. Display summary first and edit fields after selecting an item.
- **History:** calendar, imported sessions and optional source corrections.
  Session assignment and source-set corrections belong here.

Keep one active-plan selection. Put the date-range filter in historical Analysis
and History, rather than making it appear to control future recommendations.
Move the long sidebar import form behind a clear **Add workout** action.

On desktop, Overview has one full-width conclusion, followed by attention items
on the left and the next workout on the right. On narrow screens these stack.
There are no tables of source data or exercise rankings on this screen.

## Automatic set handling: proposed interpretation

The requested RIR thresholds can become a transparent application filter, but
RIR alone does not establish a set's purpose. In particular, the existing deload
policy deliberately prescribes RIR 4 or higher.

- Ordinary RIR 0–3 sets: candidates for the main progression analysis.
- RIR 4–5: light sets; do not universally call them warm-ups. A likely warm-up
  additionally precedes the main sets and uses a lower load in the same exercise.
- RIR above 5: retain the record and omit it from the main hard-set progression
  assessment under this proposed filter; do not claim it has no training value.
- Planned deload: use the block phase and deload targets; light sets remain
  legitimate deload work and do not produce missed-work/regression messages.
- Missing RIR: unknown effort, retained in history and descriptive analysis.
  Do not silently equate missing with zero or with an ineffective set.
- Timed exercises: evaluate time separately, without requiring repetition-based
  RIR. Dead hangs must not disappear because RIR was omitted.
- Existing explicit user labels/corrections take precedence over an inference.
  Manual corrections remain optional and hidden in the session details.

Implemented precedence: explicit warm-up → valid timed work → planned deload →
explicit working → ordinary RIR/sequence inference. Invalid loads/RIR are not
analysis evidence. Explicit working overrides inferred light/low-effort purpose,
but never fills in missing RIR. Unknown effort stays in descriptive/log coverage;
light/low-effort work is descriptive only unless overridden. Timed work requires
no RIR. Inferred roles carry source/reason and are never written over raw labels.

References for the distinction:
[RIR proximity-to-failure meta-regressions](https://pubmed.ncbi.nlm.nih.gov/38970765/),
[deload design consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC10511399/).
These sources do not validate the app's exact RIR cutoffs or inference rules.

## Annotations

Use **observation → evidence → next action**. For example:

> Bench Press: two more total reps at 60 kg and the same RIR. Next target:
> 60 kg × 10/10/10.

Compare like-for-like contexts: exercise identity, working-set prescription,
actual session chronology, RIR and phase. Substitutes keep separate histories.
An increased load with fewer reps must not automatically become a regression.
Missing logs must not automatically become missed training.

Each annotation has an optional **Why?** disclosure with dates, numbers, rule
and missing evidence. Limit the overview to the three highest-priority actions.
Aggregate common data gaps into one message rather than repeating an empty
target card for every exercise. Keep the complete upcoming session available
with one expansion; do not hide unchanged targets permanently.

Remove redundant top/bottom rankings and the unvalidated fatigue score from the
default experience. Present observable changes and effort patterns instead.
Do not replace them with a different opaque composite effectiveness score.

## Implementation sequence

1. **Automatic effort/set handling.** Agree the proposed rules, implement shared
   analysis policy, handle deload/missing RIR/timed work, and remove mandatory
   set-type editing from the user journey. Verify that existing explicit labels
   remain respected and raw logs are preserved.
2. **Decision annotations.** Build short, evidence-backed observations and next
   actions from existing calculations. Add data sufficiency and priority rules.
   Verify that every statement can be reproduced from its source sessions.
3. **Overview layout.** Build the conclusion plus attention/next-workout layout.
   Move the full recommendation here, consolidate repeated missing-data messages,
   and remove duplicate KPIs and default tables. Preserve desktop/mobile clarity.
4. **Analysis, Plan and History layout.** Introduce the four navigation entries,
   reorganize drill-downs, simplify plan editing, and move calendar/import/source
   corrections to their designated locations. Verify that each task has one home.
5. **Final verification and publication.** Test numerical decisions and actual
   user journeys on PostgreSQL and Streamlit Cloud, check ambiguous/low-data
   cases, update documentation and publish the completed layout.

Finish and review one numbered step before starting the next. Acceptance is
about understandable, supported decisions and reachable tasks, not the number
of charts, cards or metrics rendered.

## Step 1 delivery

- Shared interpretation in `metrics/set_interpretation.py`, with immutable kind,
  source, reason and progression eligibility in `models/set_interpretation.py`.
- Descriptive metrics retain light/unknown work; ordinary progress and plan
  working-set coverage use the shared evidence policy. Timed work needs no RIR.
- Deload context is loaded from saved session assignments and block snapshots,
  including moved workouts; the history-month filter preserves it.
- Recommendations accept automatically recognized working sets. Missing RIR still
  prevents unsupported ordinary increases, and inferred flags are not persisted.
- The Analytics label editor is removed. Optional overrides are available inside
  recorded-session details, with `Auto` restoring automatic interpretation.
- Exercise charts consume prepared metrics rather than recalculating incompatible
  strength trends from raw rows. Descriptive muscle workloads retain their dates.
- Verification covers policy boundaries/provenance, normal increases, deload and
  return, optional corrections, missing RIR, timed work, SQLite, isolated PostgreSQL
  and all six application views. No schema migration or historical relabelling.

Step 1 was committed and pushed as `7bc5f88` before starting the approved step 2.

## Step 2 delivery

- Pure `metrics/training_insights.py` prepares at most three prioritized
  observation/evidence/action annotations; immutable models retain session/set
  snapshots, interpretation provenance and any original numeric recommendation.
- Comparisons use complete ordinary work, actual chronology, separate substitute
  histories and identical context/block settings. Per-set RIR changes are explicit;
  heavier loads with fewer reps never automatically mean regression.
- The latest linked execution is the evidence barrier, including empty/incomplete
  work. First baselines, missing data, gaps and unlinked elapsed slots are grouped.
  Unlinked work is not labelled skipped; deload receives its own grouped note.
- Numeric actions reuse the selected next-workout preview only when it cites the
  same evidence and context. Historical months do not inherit today's future target.
- Annotations and optional Why/source snapshots appear in Analytics → Plan
  execution, replacing the largest-gap banner. Navigation and the Overview layout
  remain scheduled for their approved implementation steps.
- Verification: 290 unit/SQLite/Streamlit tests pass; five opt-in PostgreSQL cases
  verify dates, cross-month evidence, recommendation reuse, alternatives and deload
  in isolated rolled-back schemas. All six application views pass AppTest with
  the pinned Streamlit version. No migration or historical relabelling.

Step 2 was committed and pushed as `c21ad1f` before starting the approved step 3.

## Step 3 delivery

- Main Dashboard now opens with one full-width conclusion, recent observations
  on the left and the selected next workout on the right. The existing theme is
  preserved; columns stack below 920 px.
- Overview uses the last 28 actual days, including early/moved workouts, with
  earlier comparison evidence available. The history month does not constrain
  these current decisions. The conclusion respects today's block/deload phase.
- The next-workout preview shows at most two available targets by default,
  preferring changes. Full workout exposes every exercise, including maintained
  targets. Common missing-target reasons are grouped; setup is explained once.
- Exact next-target numbers are shown in the workout card; annotations refer
  there. Both annotations and the full recommendation are removed from Analytics.
- One persistent active-plan selection is shared with Analytics and the calendar.
  The previous five global KPI cards and two charts are removed from the landing
  page. Calendar, assignment and optional corrections remain in one collapsed
  section, with an overlay toggle, until the History navigation step.
- Verification covers current dates, context persistence, target disclosure,
  alternatives/equipment steps, empty/setup states and real desktop/mobile
  browser layout (1440 px desktop, 390 px mobile; stacked columns without
  horizontal overflow). 302 unit/SQLite/Streamlit tests and five isolated
  PostgreSQL tests pass; all six application views pass AppTest. No schema or
  progression-rule changes.

Step 3 was committed and pushed as `7194ada` before starting the approved step 4.

## Step 4 delivery

- Four navigation entries: Overview, Analysis, Plan and History. The sidebar has
  one Add workout shortcut and no global period filter or import form.
- Analysis renders one question at a time: exercise progress, plan consistency,
  muscle distribution or one body measurement. Plan comparisons and all recorded
  exercises remain available. Historical periods are local and include body data.
- Consistency is a factual annotation plus one weekly chart. Exercise comparisons
  have their own view. Rankings/fatigue-score screens are not exposed in navigation.
- History owns the calendar, session logs, assignments, replacement approval, set
  exceptions, TXT import and body input. Input opens only on an explicit action.
- Plan uses the shared active plan and edits one workout/exercise at a time.
  Draft fields and selected items survive switching exercises, workouts and pages;
  saves still create immutable versions and retain the block settings/history.
- Recorded measurement timelines include first/measurement-only dates, without
  requiring two composition records or inventing a trend. Database date forms
  (strings, dates and timestamps) are normalized before filtering.
- Verification: 311 unit/SQLite/Streamlit tests and five isolated PostgreSQL tests
  pass. All four application views and analytical questions pass on current data.
  Desktop/mobile browser checks cover navigation, a single exercise editor,
  import ownership and the calendar. No migration or new progression rule.

## Step 5 verification and publication

- Approved by the user after step 4.
- Full pinned-version verification passes: 316 tests, including five isolated
  PostgreSQL cases. Production migration preview reports no pending migrations.
- Desktop/mobile browser journeys cover all four pages, analytical questions,
  import ownership and the single-exercise editor without writing demo records.
- README and screenshots are refreshed for the four-page layout. Numerical
  evidence and operational limits are in `docs/release-validation.md`.
- Next: publish to `main`, verify that commit's GitHub Actions run, and repeat
  the read-only journey on Streamlit Cloud before marking this step complete.
