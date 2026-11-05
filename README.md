# Workout Progress Analyzer

A training dashboard that turns workout notes into a clearer next step:
**see what changed, compare it with your plan, and decide what to do next.**

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
- [Your First Plan and Workout](#your-first-plan-and-workout)
- [Training Terms](#training-terms)
- [How the Numbers Work](#how-the-numbers-work)
- [Training Plan and Next Workout](#training-plan-and-next-workout)
- [Recording and Importing Workouts](#recording-and-importing-workouts)
- [Research and Sources](#research-and-sources)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Installation](#installation)
- [Database Migrations](#database-migrations)
- [Tests](#tests)
- [Limitations & Future Work](#limitations--future-work)
- [Screenshots](#screenshots)

## Project Goal

A workout log can tell you that you lifted 60 kg. It takes more context to tell
whether you did more repetitions, used less effort, or followed the planned workout.

This project connects those pieces: **what you planned → what you recorded →
what can reasonably be compared**. It also shows how training is distributed
across muscle groups and how body measurements change over time.

For example, `60 kg × 8 reps, RIR 2` followed by `60 kg × 9 reps, RIR 2`
describes more output at the same recorded load and reserve. Here RIR 2 means
about two repetitions left in reserve. Changing the exercise, load or reserve
needs a different interpretation.

## My Role

I designed and implemented the full application, from the database to the dashboard:

- relational models for workouts, versioned plans and body measurements;
- calculation rules for comparable performance, plan execution and next targets;
- a Streamlit interface with charts, a calendar and a muscle map;
- a TXT importer, manual workout entry and optional corrections;
- automated tests for calculations, storage, import and interface behavior.

## Live Demo

**[Open the live app](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app)**

The demo uses personal training and measurement data stored in Supabase.
It is a public, single-user application with one shared dataset.

For local development, see [Installation](#installation). An existing
PostgreSQL-compatible database is required.

## Project Status

The app is deployed and supports workout import/entry, versioned plans,
progression and deload targets, muscle distribution and body tracking.
GitHub Actions checks the test suite against a disposable PostgreSQL database.

A complete database bootstrap, anonymized sample data and Docker Compose
remain planned work.

## Preview

![Current training decisions and next workout](screenshots/Overview.png)

More views, including mobile layouts, are in [Screenshots](#screenshots).

## Tech Stack

| Layer | Tools |
| --- | --- |
| Application | Python 3.11+, Streamlit |
| Calculations | Pandas, NumPy |
| Charts and muscle map | Plotly, Pillow |
| Storage | PostgreSQL / Supabase, SQLAlchemy, psycopg2 |
| Verification and hosting | Pytest, GitHub Actions, Streamlit Community Cloud |

## What It Does

The app has four pages. Each answers a different question.

| Page | Start here when you want to… |
| --- | --- |
| **Overview** | Read recent observations and the next workout's suggested targets. |
| **Analysis** | Compare an exercise, check plan consistency, inspect muscle distribution or explore body measurements. |
| **Plan** | Create a weekly routine, edit its targets or configure a training block. |
| **History** | Browse recorded sessions, link them to a plan, import workouts or correct a set. |

One active plan is shared across the app. Analysis and History have their own
date filters; changing a historical month does not change the current plan
or the next workout.

## Your First Plan and Workout

1. **Create your routine in Plan.** Name the workouts, choose weekdays and add
   exercises, for example `3 sets × 6–10 reps`.
2. **Add a workout in History → Add workout.** Enter an exercise manually or
   import a TXT note. Record RIR when you know it.
3. **Link the session to its planned workout in the History calendar.**
   This tells the app which prescription the log belongs to.
4. **Read Analysis, then Overview.** Analysis explains recorded results;
   Overview shows the upcoming target when enough comparable evidence exists.

Saving a new plan selects it automatically and updates muscle targets.
A new user may see **More data needed** before receiving numeric recommendations:
the app first needs a configured block and suitable linked history.

## Training Terms

| Term | Plain meaning | Example |
| --- | --- | --- |
| **Rep** | One repetition of a movement. | One complete bench press. |
| **Set** | A group of repetitions, or one timed hold. | 8 reps, then rest. |
| **3 × 6–10** | Three sets, each with a target of 6 to 10 reps. | 8 / 8 / 7 is within the range. |
| **RIR** | Repetitions in reserve: your estimate of how many more reps you could do. | RIR 2 means about two reps left. |
| **Working set** | A set treated as part of the main exercise work. | Separate from a warm-up. |
| **Deload** | A scheduled period with reduced training demand. | Fewer sets and lighter targets. |
| **Direct / indirect work** | The muscle is a main target / contributes to another movement. | Biceps curl / biceps contribution in a pulling exercise. |
| **e1RM** | An estimate of the load for one repetition. | A calculation from recorded weight and reps. |

**An empty RIR is unknown. RIR 0 is a recorded estimate of no repetitions left.**
The app keeps that distinction throughout its calculations.

## How the Numbers Work

### 1. Load: what does “kg” mean?

For an external-load exercise, kg is the recorded weight. Keep the same
convention between sessions, including whether dumbbell weight is per hand.

For explicitly recorded bodyweight work, the app stores three separate values:

$$
L = B + A - S
$$

Here **L** is estimated total supported load, **B** is body mass,
**A** is added weight and **S** is measured assistance, all in kg.

| Example | Calculation | Total load |
| --- | --- | --- |
| Dead hang at 80 kg body mass | 80 + 0 − 0 | 80 kg |
| Pull-up with 10 kg added | 80 + 10 − 0 | 90 kg |
| Assisted pull-up with 20 kg support | 80 + 0 − 20 | 60 kg |

Less assistance means more supported load. This estimate describes the saved
load convention; it does not measure force in an individual muscle.

The latest body-mass measurement on or before the workout date is offered as an
editable suggestion. Its value is saved with the set, so a later weigh-in does
not change an old workout. Missing mass or unknown assistance leaves the total
**unknown**; resistance-band assistance is not guessed.

### 2. Volume: how much recorded work?

For repetition-based exercises:

$$
V = \sum_i L_i \times r_i
$$

Add **load × reps** for each included set. Three sets of 10 reps at 60 kg give
`3 × 60 × 10 = 1,800 kg·reps`.

This is a descriptive workload total. Compare it within a consistent exercise
and load convention; a larger number alone does not establish better training.

**Timed holds stay in seconds.** A 45-second dead hang is one timed set:
it creates neither kg × seconds volume nor a converted number of dynamic sets.
Incomplete load totals are flagged, and charts show gaps.

<details>
<summary>Where e1RM fits</summary>

For repetition-based external-load records, the backend uses the Epley estimate:

$$
\mathrm{e1RM} = w \times \left(1 + \frac{r}{30}\right)
$$

For example, `60 kg × 10 reps` gives an estimate of `80 kg`.
This is a formula output, not a measured one-rep maximum.
Explicit bodyweight/assisted sets and timed holds receive no inferred e1RM.

</details>

### 3. Muscle distribution: where do the sets go?

One exercise can involve several muscle groups. The app assigns a saved
**factor** to each exercise–muscle relationship.

| Role | Default factor | Contribution of 4 sets |
| --- | --- | --- |
| Primary: main target | 1.0 | 4 weighted sets |
| Secondary: assisting muscle | 0.5 | 2 weighted sets |
| Stabilizer: supporting role | 0.25 | 1 weighted set |

These are allocation assumptions, not measured percentages of muscle activation.
Saved overrides can differ from the defaults.

For a single muscle group, the weekly plan target is:

$$
T_m = \sum_e s_e \times f_{e,m}
$$

**s** is the planned set count for each exercise in one reference week;
**f** is its saved factor for muscle **m**. Sum every workout in the week.

For example, suppose a plan has **6 biceps-curl sets** with factor 1 and
**8 pulling sets** with a biceps factor of 0.5:

$$
T_{\mathrm{biceps}} = 6 \times 1 + 8 \times 0.5 = 10
$$

That is **10 weighted set equivalents** from 14 exercise sets. Recorded sets
use the same factors, making the plan and log comparable.

The table then calculates:

$$
\text{Recorded / week} = \frac{\text{recorded weighted sets}}{W}
\qquad
\text{Plan \%} = \frac{\text{Recorded / week}}{T_m} \times 100
$$

**W** is the selected period's length in weeks, with a minimum of one week.
If 16 weighted sets were logged across 14 days, the result is
`16 ÷ 2 = 8 per week`. Against a target of 10, that is **80%**.

| What you see | How to read it |
| --- | --- |
| **Plan target** | One reference week of the active plan version effective today. |
| **Recorded / week** | Your logged weighted sets, averaged over the selected period. |
| **Plan %** | Recorded weekly allocation divided by the target. |
| Blue / green / amber on the map | Below / within / above the plan's ±10% comparison band. |
| Target 0 / blank | No dynamic sets planned / target unavailable. |

A new active plan changes the target automatically. The month filter changes
the recorded side. A future plan version starts affecting the target on its
effective date.

<details>
<summary>Counting details and edge cases</summary>

- A past month uses all calendar days; the current month ends today.
  **All time** spans the first through last metric date, including rest days.
- Primary-role counts are direct; secondary and stabilizer counts are indirect.
  Raw counts and weighted equivalents are different measures.
- Missing roles are not inferred from factor size. Saved weighted contributions
  remain included. Without detailed mappings, the catalog body part is used
  as a primary target with factor 1.
- Missing plan mappings or a plan read error leave targets blank, avoiding
  partial totals. With no plan, the map stays neutral; unplanned work has its
  own status.
- Explicit and inferred warm-ups are excluded. Descriptive light,
  unknown-effort and deload work remain included, so the total is not
  automatically a count of hard hypertrophy sets.
- Timed sets appear separately and do not enter the dynamic-set target.
  Muscle distribution describes the base routine; Overview handles temporary
  deload prescriptions.

The ±10% band is an application rule for comparison with a plan.
It does not diagnose undertraining, overtraining or recovery capacity.

</details>

### 4. Effort: which sets count for which question?

A recorded set can contribute to workload without supporting a progression
recommendation. The default interpretation for ordinary repetition-based work is:

| Recorded RIR | Interpretation | Used for ordinary progression? |
| --- | --- | --- |
| 0–3 | Working | Yes, subject to the other evidence checks. |
| 4–5 | Light | No, unless explicitly corrected to Working. |
| Above 5 | Low effort | No, unless explicitly corrected to Working. |
| Empty | Unknown | No numeric increase from missing effort evidence. |

A light set is inferred as a warm-up only when it precedes the first known
working set in the same logged exercise **and** uses a lower load.
A later lighter set is not automatically a warm-up.

In **History → Set interpretation · optional correction**, choose
`Auto`, `Working` or `Warm-up` when a correction is needed.
A Working override does not invent missing RIR. Warm-up excludes the set from
analytics; the original log remains available.

These thresholds are application policy. Timed exercises use duration without
requiring repetition-based RIR; planned deload work has its own context.

### 5. Performance: when are two results comparable?

Think **same exercise, same prescription, same recorded load convention**.
For a simple output comparison, per-set loads must also match.

| Earlier → later | Interpretation |
| --- | --- |
| 60 kg × 8 → 60 kg × 9, same RIR | More output at the same recorded load and reserve. |
| 60 kg × 8 → 65 kg × 7 | Load and reps both changed; no automatic regression label. |
| RIR 2 → RIR 0 | Effort changed, even if reps increased. |
| Bodyweight 80 kg → 82 kg | Total load changed, even with no added weight. |
| 30 s → 40 s, same load and context | Longer recorded hold. |

Plan-based comparisons need linked sessions. A replacement exercise keeps its
own performance history, even when it covers the original plan position.

<details>
<summary>Comparison context, evidence and charts</summary>

Comparisons match the workout name, weekday/order, exercise position, planned
and actual exercise IDs, unit, set count, target range and target RIR.
Identical prescriptions can span plan versions; changed contexts start a new
history. Load-convention changes also establish a new baseline.

Actual session date, start time and ID determine order. Unknown times sort
first; IDs break ties. Prior history remains available beyond the visible month.
The latest incomplete execution is a barrier: an older success is not substituted.

Overview looks at the last 28 actual days. A paired ordinary observation needs
complete comparable executions on different days, at most 21 days apart.
Per-set RIR must match for an output-change annotation; matching averages alone
are insufficient. One complete log can already show less reserve than planned.

Exercise charts show mean reps/time and load separately. A mean inside the
shaded band does not mean every set met the range; source details show individual
sets. Plan-context points are spaced by execution order. Amber diamonds identify
deload logs, which stay outside ordinary progress comparisons.

Recorded-exercise charts separate load conventions and reps/time. Bodyweight
and timed performance series use the same known total load. Missing or changed
loads cannot produce an automatic comparable-progress label.

</details>

### 6. Plan consistency: recorded does not always mean in range

Set coverage asks how much of the planned work has a matching log:

$$
\text{Coverage \%} =
\frac{\text{credited recorded sets}}{\text{planned sets}} \times 100
$$

If 9 of 12 planned sets are credited, coverage is **75%**.
Each plan position is capped at its planned count.

Unknown-effort logs can count toward coverage. Warm-ups and uncorrected ordinary
light/low-effort sets do not.

Coverage and range checks answer different questions. A recorded set of
5 reps may count toward coverage while falling outside a target of 6–10.
RIR is checked separately too.

Only scheduled dates **before today** enter summary ratios.
Today's open workouts and future slots do not lower the result.
An unlinked workout means “no linked record”, not proof of a missed session.

### 7. Body measurements: what changed over time?

Select weight, a circumference or a body-composition measurement in
**Analysis → Body measurements**. The chart retains first observations and dates
that have measurements but no workout.

The app reports the observed change and its dates. Whether a rising or falling
value matches your goal depends on the measurement and your intent.

## Training Plan and Next Workout

### Build a weekly routine

In **Plan**, select a saved plan or enable **Create a new plan**:

1. Set the name and effective date.
2. Add named workouts and weekdays; select one **Workout to edit**.
3. Add exercises and set their counts, ranges and unit: reps or seconds.
4. Set target RIR and an available weight step under **Progression & RIR**.
5. Save. To revise a saved routine, enable **Edit as a new version**.

A revision preserves earlier plan versions. Draft values survive switching
exercises or pages.

### Configure a training block

Under **Progression & training block**, choose a start date and a length of
6, 7 or 8 weeks. The last week is reserved for deload.

```text
Example: a repeating 7-week block
Weeks 1–6: ordinary training → Week 7: deload → next cycle
```

Weeks are seven-day intervals from the start date, including midweek starts.
Missed workouts do not move the schedule. Saving a revision preserves block
settings unless you explicitly change them.

### Understand the next target

**Overview → Next workout** previews an unlinked planned workout from today
onward. You can choose another upcoming date and expand **Full workout**.
The target is calculated from linked history; it is not written into your log.

For a plan of **3 × 6–10 reps, RIR at least 2, weight step 2.5 kg**:

| Recorded evidence | Default next target |
| --- | --- |
| At 60 kg: 8 / 8 / 7, every set RIR ≥ 2 | 60 kg: 8 / 8 / 8 — one extra rep in total. |
| At 60 kg: 10 / 10 / 10 once | Repeat the upper range to confirm it. |
| Same upper-range result on two consecutive qualifying days | 62.5 kg: 6 / 6 / 6. |
| Any set below the rep minimum or target reserve | Keep the logged loads and original range. |
| Incomplete or missing evidence | A reason for needing more data. |

The extra rep goes to the lowest-repetition set; the first set wins a tie.
The app requires a common working load for automatic increases.

**Bodyweight/assisted and timed load progression remain manual.**
The app does not assume future body mass or guess how much assistance to remove.

### Deload example

Using the same plan and a complete ordinary log of 60 kg × 10 / 10 / 10:

```text
Ordinary: 3 × 6–10 at 60 kg, RIR ≥ 2
Deload:   2 × 6    at 52.5 kg, RIR ≥ 4
Return:   resume the last comparable ordinary loads and original range
```

The default keeps half the planned sets, rounded up with at least one set,
and uses the lower rep bound. It reduces load by at least 10% in whole equipment
steps, stopping if that would exceed 20% or make the load non-positive.
Here three 2.5 kg steps give a 12.5% reduction.

Target reserve becomes `max(4, original target RIR + 2)`.
These are suggested targets, not a prediction of the reserve you will achieve.

<details>
<summary>Recommendation safeguards and developer API</summary>

- Default progression needs two upper-range confirmations on different days,
  a maximum 21-day evidence gap and a weight step no greater than 10% of the load.
  These are configurable application guards.
- Complete working sets, recorded RIR and target RIR are needed for rep increases.
  Mixed per-set loads keep individual loads/ranges. Missing evidence or a changed
  context never creates a confirmation.
- Deload uses the latest comparable normal execution in the same cycle.
  Deload logs do not compound reductions or establish ordinary baselines.
- Return uses the immediately preceding cycle's comparable normal history,
  without an increase. Old upper-range confirmations do not carry forward.
  Missing/partial latest evidence, long gaps or manually changed block settings
  prevent reuse.
- A moved planned deload remains a deload. Normal work actually performed during
  deload is excluded from normal baselines as well.
- Future records after `as_of` are not evidence. Unconfigured/not-started blocks
  get a setup message; unavailable equipment steps produce no invented load.
- Explicit alternatives use their own history and weight steps. A preview choice
  is temporary and does not edit the plan or confirm a future replacement.

The general API is
`DataManager.load_workout_recommendations(plan_id, day_id, scheduled_date, as_of=...)`.
It returns immutable `WorkoutRecommendation` / per-exercise targets with dates,
block phase, reasons and evidence IDs.

`load_normal_workout_recommendations` is a compatibility wrapper for normal dates.
Pure rules live in `metrics.progression`; use `recommend_workout` for arbitrary
dates so cycle and deload rules are applied.

Overview shows up to three observations and one full next-workout preview.
Its numeric next action comes from that same preview. **Why?** / **Why these
targets?** expose source sessions, evidence and rules. Historical Analysis does
not attach a current future recommendation to a past month.

</details>

## Recording and Importing Workouts

### Manual entry and bodyweight sets

Open **History → Add workout → Enter exercise** for reps/seconds, weight,
RIR and set purpose. For explicit bodyweight work, weight means **additional kg**;
body mass and assistance have separate fields.

History shows the saved load components.
**Body mass and load details** corrects an individual set.
Older logs keep their original kg convention until explicitly corrected.

### TXT workout import

Choose **History → Add workout → Import TXT**, or use the sidebar shortcut:

```text
Godzina 15:35-16:50

1. Incline Dumbbell Press
10x24 / 10x24 / 6x26
RIR 2 / 2 / 0

2. Lat Pulldown
12x70 / 10x70 / 11x70
RIR: 1 / 0 / 0
```

`10x24` means **10 repetitions at 24 kg**. Slashes separate sets;
the RIR values follow the same order.

| Also accepted | Example |
| --- | --- |
| Alternative set notation | `10 x 100 kg`, `10*100`, `10 @ 100` |
| Decimal comma | `10x67,5` |
| Exercise numbering | `1.`, `1)`, `1 -` |
| Inline exercise | `Bench Press: 10x100/8x110 RIR 2/1` |
| Time range | `Godzina: 10:30 - 12:45`, `Godz. 15.35 do 16.50` |
| Missing RIR | Leave it out; the value stays unknown. |

Unknown exercise names can be matched to the catalog or added as a new exercise.
Before importing explicit bodyweight sets, open **Review body mass and load types**
and check the convention and estimated total. The default preserves the TXT log's
original kg meaning. An import saves all exercises together or rolls back.

<details>
<summary>Warm-up markers and timed dead hang examples</summary>

Mark set purpose explicitly when useful:

```text
1. Bench Press
Warm-up: 10x20 / 8x40
Working: 8x60 / 8x60
RIR: 4 / 3 / 2 / 1
```

`Rozgrzewka:` and `Robocze:` work too. Unmarked sets keep an empty stored
label and are interpreted during analysis. Explicit exceptions are stored
separately from the original set values.

For dead hang, record each hold as its own duration:

```text
1. Dead hang
Working: 30s / 45s / 1:00
```

This gives three timed sets of 30, 45 and 60 seconds.
Choose **Measure = seconds** in the plan. RIR may stay empty; repetitions in
reserve do not mean seconds in reserve.

The TXT duration notation does not encode added hanging weight.
Use the import load review or manual entry to set the load components.

</details>

### Link a workout or confirm a replacement

In **History**, select a planned calendar day and link its recorded session.
The actual workout may be on another date. A session belongs to one planned slot;
removing a link preserves its log.

If you used another exercise, open **Confirm exercise replacements** on the
linked workout. For example, Machine Chest Press can cover a Barbell Bench Press
position for that session. Their performance histories stay separate.

<details>
<summary>Calendar and matching rules</summary>

- A bottom dot marks a recorded session. A top-right amber ring marks planned
  work; it fills teal when every planned slot on that date is linked.
- Slots use the plan version effective on their scheduled date.
  A new version cannot replace an already linked slot; unlink it or choose
  a later effective date.
- Matching exercise catalog IDs are automatic. Similar muscle groups alone do
  not confirm a replacement. Replacements must use the same unit: reps or seconds.
- Confirmed replacements reserve the recorded exercise for one plan position.
  Remaining exact-ID sets are allocated in plan order without double counting.
- Unlinking/deleting a session removes its replacement approvals.
  Deleting the session also removes the link; unlinking alone keeps the workout.
- Analysis uses scheduled dates for plan periods and loads moved linked sessions
  in full. A moved workout counts as recorded, but not on the planned day.

</details>

## Research and Sources

**Why no personal Min/Max for every muscle?** A study compares particular people,
exercises and counting methods. It does not reveal an individual user's minimum
effective volume or recovery ceiling.

The app therefore derives its target from **your plan**. Research explains the
programming context; it does not grade the plan or color the muscle map.

| Source | Takeaway used in this project |
| --- | --- |
| [IUSCA position stand, 2021](https://doi.org/10.47206/ijsc.v1i1.81) and [ACSM overview, 2026](https://doi.org/10.1249/MSS.0000000000003897) | Weekly volume matters for muscle growth; around 10 sets is a general reference, not a personal minimum or ceiling. |
| [Pelland et al., 2026](https://doi.org/10.1007/s40279-025-02344-w) | Distinguishing direct and indirect work helps interpret volume; 0.5 credit for indirect sets had the strongest support among the compared models. |
| [Bell et al., 2023: deload consensus](https://doi.org/10.1186/s40798-023-00633-0) | Reducing training demand is a recognized deload approach; the app's exact schedule and reductions are its own policy. |

The one-rep progression rule, confirmation count, RIR classifications, ±10% map
band and repeating 6–8 week block are transparent **application choices**.
These papers do not validate the complete algorithm or each custom muscle factor.

<details>
<summary>Muscle-specific findings and their limits</summary>

**Biceps and triceps.**
[Baz-Valle et al. (2022)](https://doi.org/10.2478/hukin-2022-0017)
compared 12–20 with more than 20 weekly sets in young trained men.
The review detected no biceps advantage for the higher category, while triceps
results favored higher volume. This does not prove equal biceps responses or
define a closed personal range.

The review counted single- and multi-joint work. Its “12–20 sets” must not be
treated as “12–20 app-weighted equivalents” or as a prescription for that many
direct sets.

**Chest.**
[Pinto et al. (2025)](https://doi.org/10.1519/JSC.0000000000005045)
found similar growth with one and three pec-deck sets per session in a small
trial in untrained men. This does not establish the optimal weekly chest range
for trained lifters.

**Broad catalog groups.**
Legs, Back and Shoulders combine different muscles or regions. A quadriceps
result cannot define a shared budget for every leg muscle. The selected evidence
does not provide exact separate limits for every catalog group.

**Allocation factors.**
Pelland's indirect-set findings do not validate a 0.25 stabilizer factor or
every exercise-specific override. Both the raw direct/indirect counts and saved
weighted contributions remain available in the calculation layer.

</details>

<details>
<summary>Exercise mapping examples and references</summary>

Wrist Curl targets wrist flexors; Reverse Wrist Curl targets wrist extensors.
These explicit rules run before the generic elbow-curl rule.
See [ACE wrist flexion](https://www.acefitness.org/resources/everyone/exercise-library/30/wrist-curl-flexion/)
and [ACE wrist extension](https://www.acefitness.org/resources/everyone/exercise-library/29/wrist-curl-extension/).

Standard straight-arm Dead hang credits forearm finger flexors/grip as primary,
with shoulder and scapular stabilization. Biceps are not a training target in
this mapping. The [finger-hang / arm-lock-off study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10623130/)
provides movement context. The mapping and its factors remain analytical labels,
not measured activation percentages.

</details>

## Architecture

Database records become domain models, then calculated results, then charts:

```mermaid
flowchart LR
    DB[(PostgreSQL)] --> Load[DataManager and data loader]
    Load --> Models[Immutable domain models]
    Models --> Metrics[Calculation rules]
    Metrics --> UI[Streamlit views]
```

| Location | Responsibility |
| --- | --- |
| `streamlit_app.py`, `ui/` | Navigation, forms and presentation. |
| `metrics/` | Calculations and decision rules, independent of Streamlit. |
| `models/` | Immutable workout, plan and recommendation types. |
| `data_loader.py`, `mapper.py` | Convert database rows into structured inputs. |
| `data_manager.py`, `db/` | Database access, imports, transactions and migrations. |

Keeping calculations separate from the interface lets tests check a rule
without opening the dashboard. Views can reshape prepared results for charts;
decision formulas stay in the calculation layer.

## Data Model

A **session** contains performed **exercises**, and each exercise contains
**sets**. The catalog maps exercises to muscle groups. Optional side tables
store explicit load details and set-purpose corrections.

Plans have dated versions, so an old session can be interpreted against the
prescription that applied then. Body measurements form independent time series;
they do not need a workout on the same date.

<details>
<summary>Core database relationships</summary>

```mermaid
erDiagram
    workout_sessions ||--o{ workout_exercises : contains
    exercises ||--o{ workout_exercises : identifies
    workout_exercises ||--o{ workout_sets : has
    exercises ||--o{ exercise_muscle_map : targets
    workout_sets ||--o| workout_set_loads : load_details
    workout_sets ||--o| workout_set_classifications : correction
    training_plans ||--|{ training_plan_versions : versions
    training_plan_versions ||--o{ training_plan_days : workouts
    training_plan_days ||--o{ training_plan_exercises : prescribes
    training_plan_versions ||--o| training_plan_progression : block_settings
```

| Tables | Stored information |
| --- | --- |
| `workout_sessions`, `workout_exercises`, `workout_sets` | Dates, performed exercises, reps/time, weight and RIR. |
| `workout_set_loads` | Explicit load type, per-set body mass and assistance. Added weight stays in `workout_sets`. |
| `workout_set_classifications` | Optional Working / Warm-up exceptions. |
| `exercises`, `exercise_muscle_map` | Catalog and muscle roles/factors. |
| `training_plans`, `training_plan_versions` | Stable plan identity and dated snapshots. |
| `training_plan_days`, `training_plan_exercises` | Named weekdays, order, sets, ranges, unit, RIR and weight step. |
| `training_plan_progression` | Versioned block start and length. No row means unconfigured. |
| `training_plan_session_links`, `training_plan_exercise_matches` | Planned-slot assignments and session-specific replacements. |
| `body_composition`, `body_measurements` | Weight/composition and body circumferences over time. |

Versions append a complete snapshot. Each starts after the previous version's
start date and cannot be backdated. Future versions do not alter earlier dates.
Multiple workouts may share a weekday; an exercise may have different targets
in different workouts.

Developer entry points:
`DataManager.save_training_plan(draft, plan_id=...)` appends a revision;
`load_training_plans()` lists latest snapshots, including future ones;
`load_effective_training_plan(plan_id, on_date)` resolves a particular date.
Draft types live in `models/training_plan.py`.

</details>

## Installation

### Requirements

- Python 3.11 or newer.
- An existing PostgreSQL-compatible database with the expected workout and
  body-tracking tables.
- Dependencies listed in `requirements.txt`.

The repository includes additive migrations, **not a complete bootstrap of the
original schema or a sample dataset**. Cloning the repository alone does not
create a ready-to-use database. For a quick look, use the live demo.

### Set up locally

These activation commands are for Windows PowerShell:

```powershell
git clone https://github.com/BaseMar/ProgressAnalyzer.git
cd ProgressAnalyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `.env` in the project root and supply your database connection:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

Preview and apply the additive migrations, then start the app:

```powershell
python -m db.migrate
python -m db.migrate --apply
streamlit run streamlit_app.py
```

Streamlit is pinned to **1.66.1** so local installs and Community Cloud use
the same renderer. Reinstall requirements after dependency changes.
A missing connection or missing base tables prevents startup data loading.

## Database Migrations

A migration adds a versioned database change. They run only when explicitly
requested, never during app startup.

| Revision | Adds |
| --- | --- |
| 001 | Training plans and dated snapshots. |
| 002 | Links between recorded sessions and planned workouts. |
| 003 | Confirmed exercise replacements. |
| 004 | Optional set-purpose corrections. |
| 005 | Versioned progression/block settings. |
| 006 | Explicit set loads and body-mass snapshots. |

`python -m db.migrate` previews pending revisions without writing.
`python -m db.migrate --apply` applies them and records successful revisions.

<details>
<summary>Migration and data-handling details</summary>

The migrations require the original catalog/workout tables, including
`exercises`, `workout_sessions`, `workout_exercises` and `workout_sets`.
They preserve historical workout values; migration 006 does not reinterpret
legacy weights. Existing plans do not receive an assumed block configuration.

PostgreSQL runs each application of pending revisions in a transaction with
a migration lock. Completed revisions are skipped on later runs. An untracked
conflicting table causes an error.

Body-mass suggestions support legacy text dates and date/timestamp columns;
invalid or future measurements are skipped without changing them.
Source data may be cached for up to five minutes; imports and corrections
invalidate the cache.

To seed exercise–muscle mappings in a configured database:

```powershell
python -m db.seed_exercise_muscle_map
```

</details>

## Tests

Tests cover calculations, model validation, parsing, filters, plan versions,
transaction rollback and Streamlit views.

```powershell
python -m pytest
python -m compileall -q db metrics models ui streamlit_app.py data_loader.py data_manager.py mapper.py
```

Five PostgreSQL integration cases need a separate test database.
Without it, they are skipped while unit, SQLite and Streamlit tests still run.

<details>
<summary>Run PostgreSQL integration tests</summary>

Use a test role with schema-creation permission:

```powershell
$env:TEST_POSTGRES_URL = "postgresql+psycopg2://user:password@localhost:5432/progress_analyzer_test"
python -m pytest
```

Each case creates a unique schema, applies all six migrations, uses synthetic
logs and rolls the schema back afterward. The tests never fall back to the app's
`DATABASE_URL`.

The [Tests workflow](.github/workflows/tests.yml) uses Python 3.12 and disposable
PostgreSQL 16 on pushes to `main` and pull requests.
Browser/release checks are recorded in [release-validation.md](docs/release-validation.md).

</details>

## Limitations & Future Work

**Current scope:** a public single-user demo. It describes recorded performance
and plan execution; it does not measure technique, muscle growth or recovery
capacity from a workout log.

Planned improvements:

- a complete database bootstrap and anonymized sample data;
- Docker Compose for repeatable local setup;
- authentication and data isolation for multiple users;
- broader free-form import coverage and linting in CI.

Implementation notes:
[analytics redesign](docs/analytics-redesign-plan.md) ·
[bodyweight and muscle distribution](docs/bodyweight-implementation-plan.md).

## Screenshots

Captured 5 November 2026 with the pinned Streamlit version and configured demo data.
Images show the interface at capture time; see
[release validation](docs/release-validation.md) for the browser checks.

<details>
<summary>Analysis: exercise, plan, muscles and body measurements</summary>

![Exercise progress](screenshots/Analysis_Exercise.png)
![Plan consistency](screenshots/Analysis_Consistency.png)
![Muscle set allocation](screenshots/Analysis_Muscles.png)
![One body measurement](screenshots/Analysis_Body.png)

</details>

<details>
<summary>Plan and workout history</summary>

![Weekly plan summary](screenshots/Plan.png)
![One exercise edited at a time](screenshots/Plan_Editor.png)
![Calendar, assignments and recorded sessions](screenshots/History.png)
![On-demand TXT import](screenshots/History_Import.png)

</details>

<details>
<summary>Mobile layouts</summary>

![Stacked training overview](screenshots/Overview_Mobile.png)
![Compact exercise editor](screenshots/Plan_Editor_Mobile.png)
![Workout calendar and session logs](screenshots/History_Mobile.png)

</details>
