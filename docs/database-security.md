# Database access security

The hosted password gate protects entry through Streamlit. PostgreSQL privileges
and Row-Level Security protect the separate Supabase Data API. These controls
serve different access paths; a website password cannot restrict public API roles.

The app uses SQLAlchemy/psycopg2 over a direct PostgreSQL connection. It does not
use Supabase client libraries, REST or GraphQL for training data.

## Database migration

Create a [fresh backup](backups.md), then preview and apply pending migrations
using the configured owner/admin connection:

```sh
python -m db.migrate
python -m db.migrate --apply
```

Migration `010_application_access_security`:

- Enables RLS on the twenty known application tables, including migration metadata.
- Revokes every table privilege from `PUBLIC` and any existing `anon`,
  `authenticated` and `service_role` roles.
- Revokes those roles' privileges on sequences owned by application tables.
- Removes automatic grants on future tables/sequences created by the migration
  role in the current schema.

It preserves table contents, sequence values and existing policies. It does not
change Supabase-managed schemas, other applications' tables or API configuration.
PostgreSQL applies the changes transactionally. SQLite needs no equivalent RLS
or Data API ACL and records the revision without those statements.

Every later migration run rechecks the controls, even when there are no pending
revisions. Add new application table names to `db.access_security.APPLICATION_TABLES`;
future objects already receive restricted defaults for the migration role.
Other creator roles have separate defaults and need a separate review.

The application backend must own its tables or use a trusted role with
`BYPASSRLS`. It retains normal SQL access; API roles do not. Do not grant blanket
access to `anon` to make the backend work. Protect the owner connection string
as a server-side secret.

## Supabase settings

If this project serves only this app, turn off its unused Data API:

1. Open the correct project in the Supabase Dashboard.
2. Open **Integrations → Data API**.
3. Turn **Enable Data API** off and save.

Also disable automatic exposure of new tables in the Data API settings if that
option is present. This complements database restrictions. Supabase's
[API security guide](https://supabase.com/docs/guides/api/securing-your-api)
documents the toggle and privilege controls. If another app uses this project's
REST/GraphQL endpoints, review that dependency before disabling the service.

## Verify

In **Security Advisor**, rerun the checks for RLS-disabled and sensitive-column
exposure. Application tables should no longer match either finding. SQL checks:

```sql
SELECT c.relname, c.relrowsecurity,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS anon_access,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS authenticated_access,
       has_table_privilege('service_role', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') AS service_access
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;
```

For the application tables, RLS should be true and all three access columns false.
Use a read-only transaction with `SET LOCAL ROLE anon` to confirm actual reads
are denied, rather than checking flags alone. Do not test unauthorized writes
against the real dataset. Confirm the backend still loads the four app routes.

The `sensitive_columns_exposed` check matches column names. For example,
`session_id` in the workout-link tables is a training-session identifier, not an
authentication token. That explains the classification, but does not make public
access to those tables acceptable. See the
[checker implementation](https://github.com/supabase/splinter/blob/main/lints/0023_sensitive_columns_exposed.sql).

Automated PostgreSQL tests recreate permissive Supabase-style grants, verify
the public roles lose access, compare every application table's records,
exercise backend writes, check future defaults and prove transaction rollback.
