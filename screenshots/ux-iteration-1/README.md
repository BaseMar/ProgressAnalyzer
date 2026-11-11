# UX iteration 1

Fictional Demo data, 11 November 2026, Streamlit 1.66.1, headless Microsoft Edge.
The existing palette and calculations are retained; this iteration changes task
entry points and the information shown first.

| Screen | Desktop | Mobile |
| --- | --- | --- |
| Overview / Progress | [1440 px](overview-1440.png) | [390 px](overview-390.png) |
| Analysis | [1440 px](analysis-1440.png) | [390 px](analysis-390.png) |
| Plan | [1440 px](plan-1440.png) | [390 px](plan-390.png) |
| History | [1440 px](history-1440.png) | [390 px](history-390.png) |

Details: [Next workout](next-workout-mobile.png), [Filters](filters-mobile.png),
[Create plan](create-plan-mobile.png), [Exercise fields](create-exercise-mobile.png),
[Editor desktop](create-plan-desktop.png), [TXT review](import-review-mobile.png),
[Successful import](import-result-mobile.png), [Manual entry](manual-mobile.png).

All four routes were checked at 360 x 800, 390 x 844, 768 x 1024, 1366 x 768,
1440 x 900, 1920 x 1080, 2560 x 1440, 3440 x 1440 and 3840 x 2160.
[Measurements](viewports.json) showed no horizontal document overflow. These are
viewport captures, sometimes scrolled to a detail, rather than full-page images.
[200% CSS zoom](plan-zoom-200.png) is a reflow smoke check; browser-native zoom,
screen-reader and physical touch-device audits were not performed.

A real TXT import and access to manual entry were checked in the isolated Demo.
Plan creation, versioned saves, draft retention and date filters are covered by
Streamlit tests. The complete isolated test run passed 630 tests; 20 cases were
skipped without PostgreSQL/external tools. The local uncommitted password-policy
change was excluded from that verification snapshot. A final focused rerun after
presentation-helper cleanup passed 36 tests. Lint, formatting, compilation and
installed dependency consistency checks passed.


The Overview captures now include three exercise-result counters (improving,
unchanged and lower output). They count the latest recorded result per catalog
exercise across comparable plan contexts, independently of the top-five limit.
No comparable pairs are shown as dashes, with the unassessed count below.

KPI verification: 646 tests passed and 20 were skipped on the isolated change
snapshot; 74 focused tests passed. Overview was checked again at all nine
viewport sizes, without horizontal document overflow.


Observation highlights: [mobile](highlights-mobile.png),
[desktop](highlights-desktop.png), [opened exercise history](highlight-history-mobile.png).
Highlights select the latest comparable exercise results before truncation, using
relative output changes. They are promoted within the existing five-item list
and are not duplicated. A negative highlight is absent when no confirmed lower
result exists. Selecting an exercise opens its complete recorded history.
Verification: 651 passed, 20 skipped in the isolated full test run; 79 focused
tests passed. Browser checks covered nine viewport sizes and an actual navigation
from the Plank highlight to its all-time Analysis history in Demo.

Next workout is centered as a complete workspace, including the section heading.
Workout details was removed; date and phase remain visible. See the updated
[mobile](next-workout-mobile.png) and [desktop](next-workout-desktop.png) captures.
41 related tests passed; centering and horizontal overflow were checked at
360, 390, 768, 1440, 1920 and 3840 px.
