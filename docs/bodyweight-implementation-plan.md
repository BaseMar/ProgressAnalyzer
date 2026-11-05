# Bodyweight exercise loads and muscle distribution

Work is split into four reviewable steps. After each completed step, stop and
ask the user for permission to commit, push, and start the next step. Do not
interpret approval of one step as approval of every later step.

1. **Load model and persistence.** Add an explicit load convention and a body-mass
   snapshot to recorded sets; preserve historical records and cover migration,
   validation, persistence and compatibility with tests.
2. **Entry and history.** Add controls for Dead hang, pull-ups and dips. Suggest
   body mass from the latest measurement on or before the workout, show its date,
   allow correction, and persist the selected value. Display body mass, added
   weight and assistance separately. Reuse the Step 1 model for atomic imports.
3. **Analysis.** Compare total supported load and time/reps within comparable
   exercise variants. Account for assistance direction, incomplete load data,
   historical convention changes and body-mass changes. Keep timed holds separate
   from dynamic hypertrophy-set guidance. Avoid reporting kg × seconds as work or
   inferring tissue force from supported mass.
4. **Muscle distribution.** Keep targets derived from the active plan. Present
   direct and indirect sets separately, with their weighted total. Replace hard
   Min/Max labels with a sourced reference range and its evidence limitations;
   use muscle-specific guidance only where supported. Do not infer an individual
   recovery ceiling from training logs alone.

## Step 1 implementation

- `SetLoad` records `external`, `bodyweight` or `assisted_bodyweight`, external
  weight, optional body mass and optional assistance. Unknown values remain
  unknown. Assistance represents a measured counterweight, not a guessed band
  resistance. Total load estimates supported system mass, not muscle force.
- `WorkoutSet.load` is optional. Absent metadata preserves the legacy convention;
  exercise names and a zero weight never trigger automatic reinterpretation.
- For explicit records, `workout_sets.weight` remains external/additional weight.
  Migration `006_set_loads` adds a side table containing the load convention and
  mass/assistance snapshot. It does not backfill or modify historical weights.
- `save_session_set_loads` saves metadata and external weight in one transaction,
  with set ownership checks. Removing metadata leaves the recorded weight intact.
  Deleting a set cascades to its metadata.
- Raw, UI, correction and plan readers carry the metadata. Reads still work
  before migration 006; explicit load writes require that migration.
- UI entry, measurement suggestions, chart labels and metric/progression changes
  belong to subsequent steps. Existing metrics still use their previous logic.

The migration has been exercised on isolated test databases. Applying it to the
application database is a separate rollout action; the application never runs it
implicitly. Deployment command when rollout is authorized:

```powershell
python -m db.migrate --apply
```

## Step 2 implementation

- History → Add workout offers Import TXT and Enter exercise. Manual entry
  records per-set reps or seconds, external/additional kg, optional RIR and set
  purpose. The suggested type for a hang, pull-up or dip is visible and editable.
- Body-mass suggestions use the latest valid measurement on/before the workout
  date, with its date displayed. Future measurements are excluded. Manual
  overrides are supported, and a missing measurement stays unknown.
- Import TXT defaults to the original kg convention. Review body mass and load
  types allows explicit per-exercise conventions and per-set additional weights,
  with a preview of the resulting total loads. Input file contents are included
  in the widget identity so a changed file cannot reuse stale load settings.
- Imports save all exercises, set purposes and load snapshots in one transaction.
  Manual entry appends one exercise to the latest session on the selected day.
  Saving opens the workout's date in History's calendar.
- History badges show time/reps, body mass, added weight, assistance and estimated
  total load. The optional load editor corrects an individual set explicitly.
  Historical weights are not automatically reclassified.
- Timed sets do not contribute a fictitious reps × kg total in history headers.
  Headers omit kg totals for bodyweight sessions pending the full analysis work.
- Migration 006 must be applied before manual entry or explicit load corrections.
  Legacy TXT import and history remain readable without it. The live database
  has not been migrated as part of these code changes.

## Step 3 implementation

- A shared load layer computes total supported mass from saved snapshots. Plan
  comparisons and insights require the same convention and known per-set loads.
  Equal additional kg with changed body mass/assistance is a changed load, not
  an automatic improvement or regression.
- Source observations include external kg, body mass, assistance and total load.
  Recorded-exercise charts split conventions and reps/time. Performance has
  separate series at each known timed/bodyweight load, while unknowns remain
  unconnected observations. Workload totals are descriptive; incomplete dynamic
  volumes have explicit missing-load counts and gaps in charts.
- Bodyweight e1RM is not inferred. Progress uses reps/seconds at the same known
  load and does not bridge a change of convention. Assistance reductions increase
  difficulty. Warm-up inference also uses comparable total loads.
- Automatic bodyweight/assisted load goals, deloads and return loads require
  manual selection: the next workout's body mass and support are not guessed.
  Unknown/mixed load conventions block automatic prescriptions. External-only
  confirmations cannot bridge a convention change.
- Timed holds count as recorded sets, with a separate count and seconds total.
  They do not contribute to the dynamic hypertrophy target or muscle-set guide;
  Muscle distribution reports allocated timed sets separately. No kg × seconds
  or duration-based hard-set equivalents are computed.
- No new migration or live database modification is part of Step 3.

Status: Step 1 committed and pushed as `c07e3a0`; Step 2 as `d3601a0`.
Step 3 approved by the user for commit and push. Step 4 is authorized; its
completion requires a new approval before commit and push.
