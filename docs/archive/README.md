# Historical plans and verification

These records describe specific releases or cleanup stages. They preserve
approval context, measurements and implementation evidence. For current
behavior and commands, use the [documentation index](../README.md).

## Feature delivery records

| Record | Historical scope |
| --- | --- |
| [Analytics redesign plan](analytics-redesign-plan.md) | Layout, interpretation and navigation delivered on 5 November 2026 |
| [Analytics release validation](release-validation.md) | Browser, database and deployment checks for the 5 November release; source of the screenshot verification |
| [Bodyweight implementation](bodyweight-implementation-plan.md) | Explicit load components, muscle distribution and their staged delivery |
| [Recommendation implementation plan](recommendation-system-implementation-plan.md) | Approved progression decisions and staged rollout; manual-start policy was later superseded by history-based starts |
| [Recommendation validation](recommendation-system-validation.md) | Checks performed for the 8 November recommendation release and its follow-up |
| [Training plan configuration](training-plan-recommendation-configuration.md) | Approved personal plan revision, saved on 8 November and effective from 10 November 2026 |

These records are not a fresh acceptance test of the current checkout. In
particular, the 5 November migration list and test totals predate later revisions.
Current policy lives in [recommendation rules](../progression-rules.md),
[calculation rules](../calculation-rules.md) and the [user guide](../user-guide.md).

## Cleanup measurements

| Stage | Report | Machine-readable evidence |
| --- | --- | --- |
| 1: English standard | Current [language guide](../language-style-guide.md) owns the conventions | Commit `0a5433b` |
| 2: inventory | [Original inventory and candidates](project-inventory.md) | Reproduce the current graph with `python scripts/project_inventory.py --json` |
| 3: regression baseline | [Method, workloads and original timings](performance-baseline.md) | [stage-3.json](../baselines/stage-3.json) |
| 4: data/cache | [Read consolidation and invalidation checks](data-access-optimization.md) | [stage-4.json](../baselines/stage-4.json) |
| 5: structure | [Module ownership and prepared inputs](project-structure.md) | [stage-5.json](../baselines/stage-5.json) |
| 6: retirement | [Removed implementations and retained coverage](code-retirement.md) | [stage-6.json](../baselines/stage-6.json) |
| 7: dependencies/checks | [Fresh-environment and CI verification](dependency-tooling-verification.md) | [stage-7.json](../baselines/stage-7.json) |

Stage 8 consolidates documentation. The maintained topic map is in the
[documentation index](../README.md); stage 9 remains final acceptance.

## Reading the evidence

Archived source-line counts, import graphs and test totals belong to the
stated commits. Paths in historical prose may describe the layout at that
release. Later retirement and formatting can change those paths and counts.
Render timings use server-side Streamlit AppTest measurements, not browser
paint or a production service-level guarantee. Live captures used read-only
guards and integrity checks; the JSON artifacts contain sanitized measurements.

The old inventory's removal candidates are historical findings. Completed
retirements are recorded in stage 6; rerun the inventory for the current graph.
The current cache contract and compatibility exports are described in
[architecture](../architecture.md), and current setup/check commands in
[local setup](../getting-started.md) and [development tools](../development-tools.md).
