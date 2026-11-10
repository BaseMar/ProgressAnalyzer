# Public demo and personal workspace

The same hosted address serves a public demo and the owner's saved training data.
Choose the workspace in the sidebar. Existing website links and embedded apps
can keep their current Streamlit URL.

| Workspace | Access | Data and lifetime |
| --- | --- | --- |
| Demo | Open to everyone; selected by default | Fictional SQLite database per browser session; resettable |
| Personal | Owner password | The persistent database selected by `DATABASE_URL` |

## Enable personal access on Streamlit Cloud

This is a one-time setup. Afterward the hosted app and database remain available
without running the app on your computer.

1. From the repository's activated Python environment, run:

   ```sh
   python -m services.personal_access
   ```

   Enter your chosen password twice. It must have at least twelve characters.
   Input is hidden. The command prints a `PERSONAL_PASSWORD_HASH = "..."` line,
   not the password itself.

2. Open the deployed app's **Settings → Secrets** in Streamlit Community Cloud.
   Keep the existing `DATABASE_URL` pointing to your real PostgreSQL/Supabase
   database. Add the exact verifier line printed by the command:

   ```toml
   DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE"
   PERSONAL_PASSWORD_HASH = "paste-the-generated-verifier-here"
   ```

   These are placeholders. Preserve your actual existing connection string;
   do not replace it with the example. Save the secrets and let the app restart.
   Streamlit documents the [Secrets settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)
   and [secret storage](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

3. Visit the usual app URL, choose **Personal** in the sidebar and enter your
   password. Your plan, history and next-workout copy action use the real database.
   Choose **Log out** when finished. Other browsers continue using Demo.

Do not put the password, verifier or database connection in Git or chat. For
local hosted-mode checks, use environment variables, a local `.env`, or ignored
`.streamlit/secrets.toml`. Missing or malformed password configuration leaves
Personal locked and keeps Demo available.

## Session behavior

Access belongs to the current browser session. A second browser/tab must unlock
Personal independently. A disconnected or expired Streamlit session can require
the password again; there is no persistent sign-in cookie.

Personal access expires after thirty minutes without an interaction, or twelve
hours after login. These checks happen on the next app interaction. Switching
workspaces and logging out clear editor drafts, selected records and password
input. They do not delete database records. Save edits before switching.

To change the password, generate a new verifier, replace `PERSONAL_PASSWORD_HASH`
in Cloud secrets and restart. Old sessions are rejected on their next interaction.
Login attempts are limited across tabs and browser sessions. The application
uses salted PBKDF2-HMAC-SHA256 with 600,000 iterations and constant-time comparison;
see the [password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

## Public sandbox

```sh
streamlit run streamlit_app.py
```

This is the entry point for the
[public deployment](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).
Demo does not resolve or connect to the personal database. Each browser session
receives generated data and a separate cache identity. Edits survive reruns.
**Reset demo** discards only that session's fictional edits.

The demo uses the same schema, writers and calculation rules as Personal.
Its database stays in memory and is released when Streamlit expires the session.
The [session-scoped resource cache](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
owns cleanup. It is not persistent storage for your own workouts.

## Direct local application

For an installation on a trusted local machine:

```sh
streamlit run personal_app.py
```

This direct entry point uses the configured database without the hosted password
gate. Publish **`streamlit_app.py`** for the shared Demo/Personal address.
Docker Compose keeps the direct entry point with its own generated PostgreSQL
database and loopback-only port, as described in the [Docker guide](docker.md).
Neither entry point copies or resets your existing personal database.
