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

Status: Step 1 approved by the user for commit and push. Step 2 is authorized;
its completion requires a new approval before commit, push and Step 3.
