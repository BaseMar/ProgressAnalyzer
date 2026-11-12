# Calculation rules and training terms

This guide explains recorded analysis, load conventions, plan coverage and
muscle allocation. The [recommendation rules](progression-rules.md) define
future targets, progression evidence and deload decisions. For dashboard controls
and import examples, see the [user guide](user-guide.md).

## Training terms

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

## How the numbers work

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

```text
e1RM = weight × (1 + reps / 30)
```

Here **weight** is the recorded external load in kg and **reps** is the number
of completed repetitions.

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

Comparisons match the stable plan-position identity, exercise order, planned
and actual exercise IDs, unit, set count, target range and target RIR.
Renaming a workout or changing its weekday preserves its stable identity.
Identical prescriptions can span plan versions; changed contexts start a new
history. Load-convention changes also establish a new baseline.

Actual session date, start time and ID determine order. Unknown times sort
first; IDs break ties. Prior history remains available beyond the visible month.
The latest incomplete execution is a barrier: an older success is not substituted.

Overview **Progress** uses recorded history independently of these plan contexts.
It selects each catalog exercise's latest actual result in the last 28 days and
compares it with the immediately preceding recorded session, even before the
window or plan. Plan links, target RIR, revisions and the recommendation-specific
21-day history cutoff do not restrict this descriptive comparison. Source dates
show the actual interval. It works without a plan.

Pairs need different recorded days, the same actual working set count, units,
per-set load convention and known total loads. For an output-change verdict,
per-set loads and actual RIR must match; matching RIR averages alone are insufficient.
Timed work does not require RIR. Warm-ups and uncorrected light/low-effort sets
are excluded. Missing/invalid values, duplicate exercise entries within a session,
changed set counts and deloads remain unassessed. The immediately previous
incomplete or deload result is not skipped to select an older positive pair.
Changed loads and reserve are contextual observations, not automatic improvement
or decline. Counts and relative-change highlights use all latest results before
the five-observation limit. Next-workout target rules remain separate and unchanged.

Exercise charts show mean reps/time and load separately. A mean inside the
shaded band does not mean every set met the range; source details show individual
sets. Plan-context points are spaced by execution order. Amber diamonds identify
deload logs, which stay outside ordinary progress comparisons.

Recorded-exercise charts separate load conventions and reps/time. Bodyweight
and timed performance series use the same known total load. Missing or changed
loads cannot produce an automatic comparable-progress label.

Analysis **Progress** restores the early/late ranking as a separate descriptive
estimate. Each eligible external-load session supplies its best existing Epley
estimate; eligible timed sessions supply their longest hold. With `N` sessions,
each window contains `min(3, floor(N / 2))` sessions. Change is
`100 × (last-window mean / first-window mean − 1)`, rounded to two decimals.
At least two positive, finite values are required, and windows never overlap.
The existing strength-convention and timed-total-load guards apply; seconds and
strength estimates never share one ranking. Warm-ups, deloads and ineligible
ordinary-effort sets cannot establish estimates. A bodyweight strength estimate
is unavailable, not zero. Top 5 contains positive changes; Bottom 5 contains the
lowest non-positive changes, with no duplication or padding. This is not the
latest-pair verdict in Overview; actual RIR can differ between ranking sessions.

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

Summary ratios include scheduled dates **before today** and linked workouts
recorded **through today**, even if scheduled for a later date. A newly recorded
and linked workout updates the summary immediately, including partial workouts.
Unperformed slots scheduled for today or later do not lower the result.
An unlinked workout means “no linked record”, not proof of a missed session.

### 7. Body measurements: what changed over time?

Select weight, a circumference or a body-composition measurement in
**Analysis → Body measurements**. The chart retains first observations and dates
that have measurements but no workout.

The app reports the observed change and its dates. Whether a rising or falling
value matches your goal depends on the measurement and your intent.

## Research and sources

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
