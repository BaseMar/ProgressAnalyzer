# Recommendation redesign validation: 8 November 2026

Status: all eight stages completed; implementation, configuration and public
release verified. This report records the stated releases, not the latest test
run. The [current progression rules](progression-redesign-rules.md) include the
9 November history-based starting-load update that supersedes the manual-start
behavior reported here.

## Implementation result

One engine implements the approved progression: repetitions, equalizing lighter
sets, repetitions at one common load, then a new common load. One complete
success is sufficient, with a 10% per-set increase limit. Deload retains sets and
repetitions, reduces load by 30-40% and targets RIR 3-4. See the
[specification](progression-redesign-rules.md).

## Verification performed

| Check | Result |
| --- | --- |
| Full local suite, Python 3.12.2 / Streamlit 1.66.1 | 504 passed; five PostgreSQL cases checked separately, for 509 cases in total. |
| PostgreSQL: isolated schemas and rollback | Five passed; rollback removed every verification schema. |
| New-rule matrix | Equalization from 60/55/55 to 60/60/60, retained repetitions, the 10% limit, corrections, plateaus, timed work and legacy bodyweight passed. |
| Migration 007 on the application database | Only position identities were added; before/after hashes of six existing tables matched. |
| Approved plan save | Version 6, ID 15, effective 10 November, with 36 positions; source version ID 14 and recorded workouts retained. |
| Compilation and change formatting | Passed. |
| Chrome at 1440 px: Overview, Analysis, Plan and History | No application exceptions or JavaScript errors. |
| Opening import and the full workout | Passed without writing fixture records to real history. |
| Chrome at 390 px: full Overview workout | No horizontal overflow or exceptions. |
| Public release and CI | Commit `a543c83` on main; CI passed; new rules confirmed in the public app. |

Application release: [`a543c83`](https://github.com/BaseMar/ProgressAnalyzer/commit/a543c830704c103b70ad5d8b69dbd3a9575e70f4).
The [release CI run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/42472144063)
passed. All four views, import opening, the full workout and the 390 px layout
were checked again in the [public app](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app/),
without application exceptions, JavaScript errors or horizontal overflow.
Expanded target explanations confirmed one complete success, equalization, the
10% per-set limit and deload with retained sets/reps and RIR 3-4.

Migration retained 127 sessions, 884 recorded exercise occurrences, 2531 sets,
five previous plan versions, 25 plan days and 174 previous exercise positions.
The sixth plan version was then appended with explicit user approval.

## Comparison against recorded history

Seventy-two decisions were replayed for two weeks starting on 8 November. The
previous code ran from a separate source checkout predating the redesign.
These comparisons retrospectively check recorded history and configuration;
they do not measure training effectiveness.

Eight decisions for 9 November used the same version, ID 14. Four one-rep targets
were unchanged, one exercise still lacked an appropriate ordinary baseline,
and three automatic starting suggestions became manual selections under the
then-approved decision 6B. Source records remained available.

The other 64 decisions used the approved configuration effective 10 November.
Differences include both the new engine and new range/RIR settings, so they are
not presented as an algorithm-only comparison under an unchanged plan. The
complete new report contained 61 manual starts after context changes, seven
one-rep targets, two missing ordinary baselines and two incomplete executions.
These are decision counts, not counts of distinct exercises. First executions
under the new configuration were expected to establish the new baseline.

At that release, legacy pull-up and dip kilograms had an unspecified convention.
The engine did not modify raw values or propose them as future body mass or
additional load. A separate case checked ambiguous repeated exercise entries
within one session.

## Follow-up: manual starting loads with visible history

Release [`b08e42d`](https://github.com/BaseMar/ProgressAnalyzer/commit/b08e42dbc5ac70c9bd60b87faa257e64c9d5aa89)
added the latest raw results from before the plan/block or without a link,
specific prescription differences, and current ranges, sets and RIR to the cards.
Repeated entries remained separate. Manual load choices appeared in the preview
and note without recording a workout or creating progression evidence. The
applicable plan version and next version's effective date were visible.

The full suite after that follow-up reported **513 passed, none skipped**,
including PostgreSQL. The [follow-up CI run](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/42474397040)
passed. Local Chrome and the public application confirmed load selection,
historical results, the RIR-change explanation, plan-version dates and no
horizontal overflow at 390 px. Browser checks changed only a test session's
preview; they did not save results to the database.

## Returning to the previous behavior

Previous application code: `4039b72db4ebf7b46c9ba4434bfeac46db35d8ba`.
Migration 007 adds a separate table, so the older application can still read its
own tables. The older `db.migrate` rejects unknown revision 007, however; retain
the newer migration runner when restoring that application release.

Do not remove the lineage table or overwrite workouts during code rollback.
The plan effective 10 November is a separate approved record: rolling back code
does not automatically revert plan parameters. Any further plan change should
create a new snapshot through the versioning mechanism.
