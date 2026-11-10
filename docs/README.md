# Documentation

Use the guides below for the current application. Each topic has one maintained
owner; summaries link to it instead of copying detailed rules or commands.

## Start here

| Goal | Guide |
| --- | --- |
| See the project and live demo | [Project README](../README.md) |
| Install the app and configure its database | [Local setup and migrations](getting-started.md) |
| Run the app and PostgreSQL together with one command | [Docker Compose demo](docker.md) |
| Understand the public sandbox and persistent personal app | [Public and personal modes](public-demo.md) |
| Create a backup and restore it into a separate database | [Backup and restore](backups.md) |
| Restrict Supabase Data API access independently of the website password | [Database access security](database-security.md) |
| Create plans, record/import workouts and use the dashboard | [User guide](user-guide.md) |
| Understand load, volume, set interpretation, comparisons and coverage | [Calculation rules](calculation-rules.md) |
| Understand starting loads, progression, deloads and bodyweight limits | [Recommendation rules](progression-rules.md) |
| Navigate code, storage, cache lifetimes and public APIs | [Architecture](architecture.md) |
| Run tests, lint/format checks or update dependencies | [Development tools](development-tools.md) |
| Write consistent English copy, comments and terminology | [Language guide](language-style-guide.md) |

## Evidence and historical context

The [v1.0.0 release notes](releases/v1.0.0.md) describe the first stable release.

The [archive](archive/README.md) contains completed implementation plans,
release checks and cleanup measurements. Its documents retain their original
dates, commit IDs, test totals and decisions. Some describe behavior superseded
by the maintained guides above. Historical commands and counts are evidence for
that release, not current setup instructions or a current test run.

Machine-readable measurements remain in [baselines](baselines/). The frozen
synthetic semantic reference is [project_baseline.json](../tests/fixtures/project_baseline.json).
The [archive index](archive/README.md#cleanup-measurements) maps each measurement
to its report. Baseline data should not be regenerated to hide a behavior change.

The [final cleanup validation](archive/final-cleanup-validation.md) records the
stage 9 acceptance results, performance comparison, browser coverage and remaining
limits for its stated application commit.

## Keep documentation current

When behavior changes, update its maintained guide and verify the corresponding
code/configuration. Link from summaries and related guides. Keep runtime setup
in `getting-started.md`, development commands in `development-tools.md`, the
storage/cache contract in `architecture.md` and progression policy in
`progression-rules.md`.

Preserve historical evidence in `archive/`; label its scope and link to the
maintained guide. Check relative links, heading anchors and screenshot paths
after moving documents.
All commands in the maintained guides run from the repository root unless
explicitly stated otherwise.
