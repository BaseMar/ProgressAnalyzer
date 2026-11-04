# Analytics-first layout proposal

Status: approved, 5 November 2026. Step 1 is implemented and verified.
Steps 2–5 have not started. The user requires explicit approval
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

Next action: obtain the user's approval before starting step 2 (decision
annotations). No steps 2–5 are included in this delivery.
