# Recommendations and progression: approved rules v1.1

Date: 9 November 2026. Update: automatically read starting loads from the user's
full exercise history after a plan change.
Calculation version: `double-progression-2026-11-v2`.

## Goal and confirmed preferences

The goal is hypertrophy and strength. The user records repetitions in reserve
(RIR) for working sets and warm-ups, accepting estimation error. Rest is usually
about three minutes; later isolation exercises use a rest period chosen by feel.
This is a stated habit, not a measurement of every historical rest interval.

Different loads may reflect finding a starting load or fatigue. The default model
is not a planned pyramid or a heavy top set with separate back-off progression.
The saved plan, recorded results and recommendation remain separate information.

The user approved answers 1B, 2A, 3B, 4A, 5A, 6B, 7 (existing notes) and 8B,
then clarified load equalization and the additional parameters below. The
9 November update replaces manual starts after context changes with history-based
starting loads where usable records exist. All thresholds are application rules,
not physiological laws.

## Double progression with load equalization

1. After a complete execution within range and with the required reserve, try
   one additional total repetition in the first set below the upper bound.
2. Equalization or a weight increase requires every planned set to reach the
   upper bound at its current load, with RIR at least equal to the target.
3. One complete comparable execution is sufficient. A second is not required.
4. If loads differ, first raise lighter sets toward the established first
   working load. Raised sets return to the lower repetition bound; sets already
   at the reference load retain the upper-bound target.
5. Every increase, including equalization, is limited to 10% of that set's
   previous load. Choose the largest number of available equipment increments
   within that limit and at or below the reference load. Close larger gaps
   over several successful executions.
6. Only a complete success at one common load permits the next common load:
   one available increment, with the lower repetition bound for every set.
7. Do not increase weight, repetition targets and set count simultaneously.
   Reserve and technique take priority over achieving the number on the card.

The reference is the established first working load, rather than the maximum
found anywhere in history or in a later calibration attempt. If no available
increment fits, explain the equipment limitation and leave the equipment, range
or load decision to the user. Do not invent unavailable microloading.

## Ordinary decision matrix

Example: 8-12 reps, target RIR 2, equipment increment 2.5 kg. Rows involving an
increase assume sufficient reserve in every set. Targets do not predict results.

| Recorded execution or situation | Next decision |
| --- | --- |
| 60 x 10 / 60 x 9 / 60 x 8 | 60 x 11 / 60 x 9 / 60 x 8. |
| 60 x 12 / 55 x 11 / 55 x 12 | 60 x 12 / 55 x 12 / 55 x 12. |
| 60 x 12 / 55 x 12 / 55 x 12 | 60 x 12 / 60 x 8 / 60 x 8. |
| 60 x 12 / 60 x 12 / 55 x 12 | 60 x 12 / 60 x 12 / 60 x 8. |
| 60 x 12 / 50 x 12 / 50 x 12 | 60 x 12 / 55 x 8 / 55 x 8: an intermediate step within the 10% limit. |
| 60 x 12 / 60 x 8 / 60 x 8 | 60 x 12 / 60 x 9 / 60 x 8. |
| 60 x 12 / 60 x 12 / 60 x 12 | 62.5 x 8 / 62.5 x 8 / 62.5 x 8. |
| One set at RIR 1 above the minimum, with target RIR 2 | No increase or automatic reduction; perform the range with the required reserve. |
| RIR 0 at 12 reps | First stop earlier within the range; do not assume an exact conversion of two fewer reps into two more RIR. |
| RIR below target at 8 reps | After the first such execution, reduce that set by one available increment if the result remains positive. |
| Fewer than 8 reps, reserve at or below target | Correct that set's load after the first execution. |
| Below the minimum with substantial reserve | First perform the prescribed range with reserve, without automatically adding weight. |
| Only a later set fails | Correct that set; do not automatically lower the entire exercise's starting load. |
| No positive lower equipment setting | Select the affected set's load manually. |
| Some sets exceed the upper bound | Cap targets at the upper bound; do not encourage further overshooting. |
| Missing sets or RIR | No numeric increase; explain the missing evidence. |
| Several recorded entries match one plan position | Require an explicit History assignment; do not select an arbitrary success. |

## Starting loads and comparability

After a change to the plan, order, range, RIR, set count or block, read starting
loads from the latest usable execution of the exact exercise across all history.
Include previous plans and unlinked sessions. Preserve working-set load order;
additional planned sets repeat the last working load. Later heavier trials do
not raise the start above the first working load.

Exclude warm-ups, known deloads, invalid entries and future dates. Show the source
alongside the current range and RIR. Reading history does not create executions
or change recorded results.

A starting-load suggestion does not confirm a weight increase. A recorded and
linked execution in the current context enables progression under the existing
rules. When usable history is unavailable, manual selection remains a fallback:
complete choices are remembered, and the form disappears once all are filled.
Actual history takes priority over remembered manual choices.

Ordinary progression from an established baseline can still change targets
automatically. A block calendar is not required for ordinary recommendations.

Comparisons require the same actual exercise, position or role, unit, set
structure and prescription. Plan positions have stable history keys. Renaming
a workout or changing only its weekday does not discard history. Repeated
positions of the same exercise retain separate keys. Legacy keys are initialized
from the plan, workout position and exercise occurrence; they do not reconstruct
historical role labels that were never recorded.

Chronology uses actual execution dates. Results after `as_of` are excluded.
Automatic increase confirmations do not skip a latest incomplete execution to
find an older success. An unlinked session is not evidence of a missed workout.
Alternatives require explicit selection and their own equipment increment.
Analysis filters do not change future targets. Different kg conventions are not
interchangeable.

## RIR, set purpose and rest

RIR is an estimate. Do not correct it automatically or assume a universal error
of one repetition. RIR 0 is valid; missing RIR stays unknown. Readiness to increase
and the need to reduce a load are separate decisions.

Explicit purpose labels and corrections take priority. The importer accepts
`warm-up` and `working`, plus the legacy Polish aliases `rozgrzewka` and `robocze`.
For unlabelled history, the user chose the existing heuristic: RIR 0-3 is a
working-set candidate, 4-5 is light effort and above 5 is low effort. An inferred
warm-up must also precede working sets and use a lower load under the same
convention. Missing RIR remains unknown. The inference source is visible and
does not overwrite raw records.

An explicitly working set at RIR 4 remains working. An explicit warm-up at RIR 2
remains a warm-up. Recording RIR alone does not determine purpose.

Unknown rest does not block the entire system, but limits explanations of why
results differ. A repetition drop alone does not identify shorter rest or lost
strength. Measuring every rest interval is not a required input.

## Possible plateaus and long gaps

A possible plateau is four complete comparable executions at the same loads
with sufficient reserve, without an increase in total repetitions or confirmed
reserve improvement. Executions must occur on separate days, no more than
21 days apart. A complete upper-bound execution ready for an increase is not
labelled a plateau.

Confirmed RIR improvement within that window requires two consecutive executions
with the baseline's per-set repetitions, no lower reserve in any set and higher
reserve in at least one. An average must not hide deterioration in individual
sets. One higher reading is insufficient. The plateau flag is an observation:
it does not add sets, change exercises or diagnose overtraining.

More than 21 days since the last comparable execution blocks automatic
progression. Older results can still supply a starting load with a source-age
notice, without assuming a particular percentage of strength loss.

## Automatic deload and return

Deload occurs in the final week of the configured cycle. Retain all sets and
the actual repetitions from the last comparable ordinary workout. Reduce each
load by at least 30% in whole equipment increments, choosing the first available
setting whose reduction does not exceed 40%. If no positive setting fits,
require manual selection. Target RIR is 3-4; actual reserve is logged after the
set and is not calculated from the load-reduction percentage.

Example: ordinary 60 kg x 10/10/10, with a 2.5 kg increment, becomes deload
40 kg x 10/10/10 at target RIR 3-4. Recorded 12/10/9 remains 12/10/9 instead of
resetting to the lower bound.

Deload is neither ordinary success nor regression. Do not compound reductions
from successive lighter sessions. A moved deload session remains a deload;
an ordinary workout performed during the deload period does not confirm normal
progression either. After deload, resume the last ordinary baseline from the
previous cycle without an immediate increase. The first ordinary execution
checks that baseline. Completeness, comparability and history-age limits still
apply. A plan revision retains the calendar unless the user explicitly changes it.

## Timed work, bodyweight and automation limits

- Time: add up to five seconds to the first set below the ceiling, capped at the
  range maximum. Repetition-based RIR is not required. At the ceiling, select
  a new range or load manually. Timed/load-setting deloads also remain manual.
- Bodyweight and assistance: suggest repetitions and read recorded additional
  load and assistance without automatically increasing difficulty. Less
  assistance increases difficulty. Future body mass is not assumed or converted
  into kilograms of muscle force.
- Legacy pull-up, dip and similar records with an unknown convention show
  repetition/time targets with manual load selection. Recognizing an exercise
  type limits automation but does not change the meaning of recorded kilograms.
- Exercise-specific user confirmation that legacy kg represented body mass only
  allows 0 kg additional load. Store confirmation separately and preserve the
  original kg. Explicit newer additional-load records take priority. Recorded
  0 kg needs no confirmation.
- Unknown body mass or assistance in an explicit convention limits load comparisons.
- Unilateral sets require a consistent per-side convention. The model does not
  measure each side separately or confirm an unrecorded second side.
- Drop sets, rest-pause and forced reps require a separate variant or manual
  selection. Do not infer these techniques from kg and reps alone.
- The system does not assess technique, pain, illness or injury from a log and
  is not a rehabilitation or fatigue-diagnosis algorithm.

## Shared output and rollout

Each recommendation contains an action, per-set goals, target reserve, primary
reason, source sessions, limitations and rules version. Overview, Analysis and
the workout note share the same output. Targets are not recorded executions.

Priority: deload/return, validation, history-based start or manual fallback,
minimum-failure correction, insufficient reserve, equalization, a new common
load, an additional repetition/time target, then maintenance. A plateau is an
additional observation.

The approved [36-position plan configuration](training-plan-recommendation-configuration.md)
was saved as version 6 (ID 15), effective from 10 November 2026. Historical
versions and executions remain intact. Stages and acceptance are recorded in
the [implementation plan](recommendation-system-implementation-plan.md).

## Research context and application-specific rules

| Source | Finding and limitation |
| --- | --- |
| [ACSM 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/) | Goals and individualization matter; failure is not required. It does not prescribe this exact algorithm or an optimal RIR for every exercise. |
| [ACSM 2009](https://pubmed.ncbi.nlm.nih.gov/19204579/) | Describes 2-10% increases after exceeding target repetitions. It is not the source of the user's one-success or set-equalization rule. |
| [Plotkin et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9528903/) | Supports repetition and load progression, without proving superiority of this particular scheme. |
| [Russo et al., online 2025](https://doi.org/10.1080/10833196.2025.2564026) | RIR accuracy depends on conditions; there is no universal one-repetition tolerance. |
| [Bell et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10511399/) | Supports individualized deloads. Retaining sets and reducing load by 30-40% are user choices, not a mandatory protocol from this source. |
| [Senna et al. 2011](https://pubmed.ncbi.nlm.nih.gov/21993029/) | Rest duration affected repetitions; without measuring it, the cause of a particular drop cannot be established. |
| [Singer et al. 2024](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1429789/full) | Hypertrophy occurs with different rest intervals; the study does not establish one exact duration for all exercises. |
