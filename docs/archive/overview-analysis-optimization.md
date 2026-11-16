# Overview and Analysis loading optimization

Measured on 16 November 2026 against baseline commit `d7c2a8e` and the subsequent
optimization working tree. Current behavior is described in
[architecture](../architecture.md) and the [user guide](../user-guide.md).
Individual samples and SQL counts are in
[the measurement JSON](../baselines/overview-analysis-2026-11-16.json).

## Findings and changes

The personal PostgreSQL workload contained 132 sessions and 2,609 sets. Exercise
metrics took about 64 ms on preloaded inputs. Repeated database round trips were
the main cost in the slower views: the baseline warm Overview issued 29 SQL
statements, Plan consistency 24 and Muscles 12.

- Overview rendered both tab bodies on every rerun. It now computes only the
  open tab, remembers that tab across navigation and uses the existing loader
  when switching tabs. Progress requires no plan reads or future targets.
- Overview and Analysis plan selectors now read the latest plan names without
  fetching prescriptions for every plan. Full version readers join days,
  prescriptions, optional lineage and block settings in one child query.
- Linked-plan targets join lineage directly; performance bounds use one query.
- Source loading and linked-history reads borrow one connection for each short
  read group. It is released before rendering widgets or writing records.
  Optional muscle-map failures roll back a savepoint, preserving the remaining
  source reads on PostgreSQL. Existing render-local cache invalidation remains
  in force; plan snapshots still refresh on each render.

## Measurements

Times are server-side milliseconds from the real `personal_app.py` AppTest path.
Each view has one cache-cold sample and three unchanged warm reruns; the warm
column is their median. Python imports and the connection pool were initialized.
Analysis uses All time. These timings exclude browser paint, frontend transfer,
fresh-process startup and initial public-demo generation. Network variation and
small sample counts limit timing precision.

| View | Cold before → after | Warm before → after | Warm SQL before → after |
| --- | ---: | ---: | ---: |
| Overview: Progress | 5763 → 2220 | 2864 → 59 | 29 → 0 |
| Overview: Next workout | 5763 → 3309 | 2864 → 1967 | 29 → 20 |
| Analysis: Progress | 2750 → 1697 | 202 → 129 | 0 → 0 |
| Analysis: Exercises | 2751 → 1707 | 136 → 138 | 0 → 0 |
| Analysis: Plan consistency | 4443 → 2733 | 2165 → 1467 | 24 → 15 |
| Analysis: Muscles | 4508 → 2983 | 1177 → 877 | 12 → 4 |
| Analysis: Body measurements | 2541 → 1584 | 92 → 40 | 0 → 0 |

Both Overview rows share the same before sample because the original renderer
computed both tabs together. The after samples render the selected tab only.
Changing an upcoming workout after loading took 1889 ms (20 statements) after
the optimization. Exercises was already fast once the source cache was warm;
its 136/138 ms samples represent effectively unchanged performance.

Next workout and Plan consistency remain the slowest warm views because their
plan and linked-history reads refresh each render. PostgreSQL request latency,
transaction setup/cleanup and fetching contribute beyond pure metric time.

## Validation

All five Analysis output hashes match the before capture. Concatenating the
separate Overview tabs' displayed metrics, copied notes, recommendation cards and
tables reproduces the original combined Overview output hash. The frozen
synthetic semantic reference also passes unchanged.

The live runner enforced PostgreSQL read-only transactions, rejected write SQL
and checked table fingerprints before and after. No application records changed.
Savepoint controls are allowed by the probe and counted in SQL samples.

The local suite passed 779 tests, skipped 20 integration cases and deselected one
preexisting password-length test affected by an unrelated local edit. Ruff check
and format checks passed. Browser checks covered lazy Overview rendering,
all Analysis tabs, remembered navigation and a 390 px mobile viewport.
