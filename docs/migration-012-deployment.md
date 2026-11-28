# Deploy Phase 2B with migration 012

Use this runbook for the hosted PostgreSQL Personal workspace. Schedule one
maintenance window that covers the write pause, backup, restored-copy rehearsal,
migration, hosted revision change and smoke tests. Budget the window using the
restore and migration durations measured in rehearsal. The operator approves the
window, migration and application release separately.

## Compatibility and release order

| Application and schema | Operational result |
| --- | --- |
| Phase 2B on 011 | Streamlit can start, and some Personal reads and writes work. Unlinking or deleting a plan with linked sessions requires 012. New links on 011 do not create provenance. Upgrade before using Personal on Phase 2B. |
| Phase 2A on 012 | Its normal app paths can still read and write the old tables. It ignores retained evidence and its link, unlink and plan deletion writes bypass capture. Its migration CLI rejects the unknown 012 revision. Keep old writers disconnected. |
| Phase 2B on 012 | Supported. Personal uses the migrated database. Demo creates a separate, freshly bootstrapped SQLite database. |

The hosted `streamlit_app.py` and standalone `personal_app.py` do not migrate
Personal data on startup. Community Cloud tracks a configured repository,
branch and entry point and can update automatically. If it tracks `main`, the
approved merge is the deployment trigger. Keep the release branch unmerged
until production migration and verification are complete. Confirm the actual
deployment coordinates in the dashboard. [Community Cloud update behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#update-your-app)

## 1. Confirm the database and release identity

Use Bash in an isolated operator checkout of the exact approved Phase 2B commit,
with the app dependencies and PostgreSQL clients matching the server major
version. Use a direct or session-mode PostgreSQL owner connection with the
expected TLS settings. The migration role needs DDL, backfill access through
RLS, and control of the application objects. If the runtime uses a separate
role, verify its approved access to the new table on the restored copy.

Record the approved commit, the last working deployment revision, the expected
Supabase project reference, endpoint, database name and schema `public` from
the dashboards. Store the current hosted connection and verifier in the
operator's protected vault before editing settings. Keep shell tracing off.
Load the approved operator URL without putting it in the command history.

```bash
set -euo pipefail
set +x
git rev-parse HEAD
read -rsp 'Verified production owner URL: ' DATABASE_URL
printf '\n'
export DATABASE_URL
```

Define this helper for subsequent read-only SQL. It passes the same explicit URL
used by the migration and backup tools without putting credentials on the command
line. On a connection failure, stop and diagnose privately.

```bash
phase2b_read() {
  python -c '
import os, sys
from sqlalchemy import create_engine

engine = create_engine(os.environ[sys.argv[1]])
try:
    with engine.begin() as connection:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        for row in connection.exec_driver_sql(sys.stdin.read()):
            print(*row, sep="\t")
except Exception as error:
    raise SystemExit(f"Read-only check failed ({type(error).__name__})") from None
finally:
    engine.dispose()
' "$1"
}

phase2b_read DATABASE_URL <<'SQL'
SELECT current_database(), current_schema(), current_user,
       inet_server_addr(), inet_server_port(),
       current_setting('server_version_num');
SQL

phase2b_read DATABASE_URL <<'SQL'
SELECT revision FROM public.schema_migrations ORDER BY revision;
SQL
```

Confirm the entered URL's endpoint and project reference independently of the
SQL output. The database name alone may be shared among multiple projects.
Expect schema 011, including `011_exercise_load_profiles` as the last revision.
Stop on any mismatch or unexpected revision.

## 2. Pause Personal writes

Stop local Personal instances, importers, scripts and any other writers. In
Community Cloud **Settings → Secrets**, remove `PERSONAL_PASSWORD_HASH` from
the active configuration and replace `DATABASE_URL` with the following
maintenance placeholder, then reboot. Verify that no independent environment
setting overrides either key. Close previously authenticated tabs and verify
from a fresh browser session that Personal is unavailable and Demo loads.
Keep the verified production credentials in the vault and operator environment.

```toml
DATABASE_URL = "postgresql+psycopg2://maintenance:maintenance@127.0.0.1:1/maintenance"
```

A reboot alone is insufficient. Verify at the database that old writer
connections and transactions have drained. If deployment uses a distinct
database login for the app, you can fence it with the provider's access controls
and disconnect its old sessions, while keeping the migration and recovery
login usable. If the app shares the operator role, verify shutdown or isolation
of every old writer before proceeding. The project lock serializes migration
runners. It does not fence application writes.

```bash
phase2b_read DATABASE_URL <<'SQL'
SELECT usename, application_name, client_addr, state, count(*)
FROM pg_stat_activity
WHERE datname = current_database() AND pid <> pg_backend_pid()
GROUP BY usename, application_name, client_addr, state
ORDER BY usename, application_name, client_addr, state;
SQL
```

Do not proceed with unidentified writer sessions or if the pause cannot be
enforced. Keep the pause in effect through step 9.

## 3. Create and verify a protected backup

Use an encrypted operator directory outside the checkout, accessible only to
the operator. Select a new filename and keep the checksum separately with the
release record. The [backup guide](backups.md) describes the public-schema scope
and how to use matching PostgreSQL utilities. Save provider recovery information
and the required owner, runtime grants, roles and configuration through the
provider's approved process. The application dump omits these grants and roles
and excludes provider-managed schemas.

```bash
umask 077
read -rp 'Existing encrypted backup directory: ' backup_dir
backup_file="$backup_dir/workout-pre012-$(date -u +%Y%m%dT%H%M%SZ).dump"
python -m db.backup create --url-env DATABASE_URL --file "$backup_file"
pg_restore --list "$backup_file" > "$backup_file.toc"
grep -E 'schema_migrations|training_plan_session_links|workout_sets' "$backup_file.toc"
sha256sum "$backup_file" > "$backup_file.sha256"
sha256sum --check "$backup_file.sha256"
```

Record the count of current links for the rehearsal and final comparison.

```bash
phase2b_read DATABASE_URL <<'SQL'
SELECT count(*) FROM public.training_plan_session_links;
SQL
```

## 4. Rehearse on an isolated restore

Provision a separate empty PostgreSQL database with network access limited to
the operator. Match the production PostgreSQL major version and roles and
defaults that affect the application. A production dump contains Personal data.
Keep this copy protected under the same access and retention rules. Verify its
URL and target identity separately and never make it a public Demo backend.

```bash
read -rsp 'Verified isolated restore owner URL: ' RESTORE_DATABASE_URL
printf '\n'
export RESTORE_DATABASE_URL
phase2b_read RESTORE_DATABASE_URL <<'SQL'
SELECT current_database(), current_schema(), current_user,
       inet_server_addr(), inet_server_port();
SQL
python -m db.backup restore --url-env RESTORE_DATABASE_URL --file "$backup_file"
DATABASE_URL="$RESTORE_DATABASE_URL" python -m db.migrate
DATABASE_URL="$RESTORE_DATABASE_URL" python -m db.migrate --apply
DATABASE_URL="$RESTORE_DATABASE_URL" python -m db.migrate
```

Expect only `012_session_provenance` before the upgrade and `Pending: none`
after it. Run step 7's SQL with `RESTORE_DATABASE_URL`, compare counts with
production, and check read/write access using the expected runtime role. Run the
approved app privately against the restored copy. Use a dedicated test plan
and test sessions to exercise import, link, replace, unlink, relink, a moved
deload, plan deletion, and the next-workout preview and copy action. Verify that
the workout's sets, identities, set purposes, loads and RIR agree before and
after unlinking. Also rehearse restoring the pre-012 backup into a second empty
target and running the Phase 2A app against it. Stop if any checks fail or the
measured cutover and recovery time exceed the window.

## 5. Preview production migrations

Reconfirm the paused writers and production identity from steps 1 and 2, then
run the read-only preview from the approved Phase 2B checkout.

```bash
python -m db.migrate
```

Proceed only if the complete output is `Pending: 012_session_provenance`.

## 6. Apply only after explicit operator approval

Confirm the checked backup, completed rehearsal, time remaining in the window,
verified target and fenced old writers. Ask the responsible operator for an
explicit go decision. Until then keep the database and the tracked hosted
branch at their current revisions. After approval, run once.

```bash
python -m db.migrate --apply
python -m db.migrate
```

Expect `Applied: 012_session_provenance` and then `Pending: none`. PostgreSQL
commits creation, backfill, revision entry and access hardening together. The
`--apply` path also reapplies access hardening to existing app objects and
migration-role defaults, so use the read-only preview to check a completed run.

## 7. Verify coverage and PostgreSQL security

Run these checks before any Phase 2B writer touches the data. Snapshot count must
equal the prior linked session count. `missing` and `unexpected` must both be
zero. Unknown phase is valid for links without a determinable block phase.

```bash
phase2b_read DATABASE_URL <<'SQL'
SELECT revision FROM public.schema_migrations ORDER BY revision;
SQL
phase2b_read DATABASE_URL <<'SQL'
SELECT (SELECT count(*) FROM public.training_plan_session_links) AS links,
       (SELECT count(*) FROM public.workout_session_provenance) AS snapshots,
       count(*) FILTER (WHERE p.session_id IS NULL) AS missing,
       count(*) FILTER (WHERE l.session_id IS NULL) AS unexpected
FROM public.training_plan_session_links l
FULL JOIN public.workout_session_provenance p USING (session_id);
SQL
phase2b_read DATABASE_URL <<'SQL'
SELECT phase, count(*) FROM public.workout_session_provenance GROUP BY phase;
SQL
phase2b_read DATABASE_URL <<'SQL'
SELECT c.relname, c.relrowsecurity, pg_get_userbyid(c.relowner) AS owner,
       pg_get_serial_sequence('public.workout_session_provenance', 'session_id')
FROM pg_class c WHERE c.oid = 'public.workout_session_provenance'::regclass;
SQL
phase2b_read DATABASE_URL <<'SQL'
SELECT r.rolname,
       has_table_privilege(r.oid, c.oid,
         'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS table_access,
       has_any_column_privilege(r.oid, c.oid,
         'SELECT,INSERT,UPDATE,REFERENCES') AS column_access
FROM pg_roles r CROSS JOIN pg_class c
WHERE r.rolname IN ('anon','authenticated','service_role')
  AND c.oid = 'public.workout_session_provenance'::regclass;
SQL
phase2b_read DATABASE_URL <<'SQL'
SELECT a.privilege_type
FROM pg_class c
CROSS JOIN LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) a
WHERE c.oid = 'public.workout_session_provenance'::regclass AND a.grantee = 0;
SQL
```

Expect RLS `True`, the approved owner, no owned sequence for this table, both
access flags `False` for every existing API role, and zero public ACL rows.
Run the [database security checks](database-security.md#verify) for the other
application tables and inspect any provider security warnings. The new table
uses the recorded session's key. Migration 012 creates no sequence and adds no
Data API grants. If the app uses a separate runtime login, compare its access
with the approved role setup exercised in rehearsal. Stop on any missed link,
unexpected access, revision or owner.

## 8. Deploy the approved application revision

While Personal remains fenced, release the tested Phase 2B change using the
deployment's verified source. If it tracks `main`, merge only the approved PR
now, confirm that the resulting tree matches the tested change, and watch the
Community Cloud logs. Reboot the app to clear old sessions and imports. Confirm
the source branch, entry point and revision correspond to the intended release.
[Community Cloud reboot](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/reboot-your-app)

## 9. Verify Personal and Demo

Keep regular users and all old clients out. Verify the hosted Demo opens in a
fresh unauthenticated browser session. Open Overview, Analysis, Plan and History,
check next-workout preview and copy, and make a disposable Demo edit. Open a
second session to verify the edit is isolated. Reset Demo and verify the test
edit disappears.

For the production Personal read smoke, run the approved revision privately with
the exact approved runtime connection in `DATABASE_URL`, the vaulted Personal
verifier in `PERSONAL_PASSWORD_HASH`, and libpq read-only mode. Leave the hosted
Personal fence in place during this check. Use the rehearsed restore for write
smokes involving records.

```bash
read -rsp 'Verified production runtime URL: ' SMOKE_DATABASE_URL
printf '\n'
read -rsp 'Vaulted Personal verifier: ' SMOKE_PERSONAL_HASH
printf '\n'
DATABASE_URL="$SMOKE_DATABASE_URL" PERSONAL_PASSWORD_HASH="$SMOKE_PERSONAL_HASH" \
  PGOPTIONS='-c default_transaction_read_only=on' \
  streamlit run streamlit_app.py --server.address 127.0.0.1
unset SMOKE_DATABASE_URL SMOKE_PERSONAL_HASH
```

Confirm the private Personal login, expected plan and history, linked and
retained context display, next-workout preview and copy action. Re-enter Demo
and verify it is separate. Check for schema or permission errors. Stop the
private app after the check. Do not create or edit workout records as part of
the production smoke.

## 10. Resume usage

After operator sign-off, restore the vaulted hosted runtime URL and verifier,
reenable the designated runtime login if fenced, and reboot. Confirm the
hosted Personal login and read paths in one fresh browser session. Check the
public Demo again and monitor the app and database logs. Reopen normal use only
on the approved Phase 2B revision. Retain the backup and recovery record under
the configured policy and remove rehearsal copies according to that policy.

## Rollback and stop conditions

- **Migration failed.** Keep the fence. Check the ledger, table existence and
  access state using a fresh connection. A failed migration leaves 011 and no
  provenance table. Diagnose privately, rehearse the correction, then seek a new
  go decision. If 011 and its access controls are intact, the operator can
  reopen the unchanged Phase 2A release with its previous configuration.
- **012 committed but no production writes resumed.** Prefer fixing forward
  with the fence up. For a full rollback, restore the verified pre-012 dump to
  a separate empty recovery target as in step 4. Re-establish the approved
  owners, runtime privileges and access controls. Using the Phase 2A checkout
  and that recovery URL, verify `python -m db.migrate` reports `Pending: none`.
  Run `python -m db.migrate --apply` from Phase 2A against that recovery URL to
  reapply its baseline access hardening. Bring up the previous application
  revision privately and verify data and access. If Cloud tracks `main` and
  already loaded Phase 2B, land a reviewed revert of its release change and
  confirm the previous application tree is back. While Personal stays fenced,
  update the vaulted runtime URL to the recovered database. Follow step 10
  with the recovered URL only after operator approval. Retain the migrated
  database for diagnosis.
- **Writes resumed on 012.** Fence writes again and take a protected backup of
  012 before recovery. Restoring the pre-012 snapshot would lose later changes
  unless they are separately reconciled. Require a separate data-recovery and
  cutover decision. Keep Phase 2A writes off the 012 database while resolving
  the incident.

There is no down-migration. Deleting ledger rows or dropping the provenance
table does not restore earlier security or application behavior. For a restore
to a different project, separately verify provider configuration, access,
secrets and any data outside the application dump before opening it to users.
