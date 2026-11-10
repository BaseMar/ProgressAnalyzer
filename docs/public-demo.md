# Public demo and personal application

The project has two explicit entry points sharing the same views and rules.

| Entry point | Data source | Lifetime |
| --- | --- | --- |
| `streamlit_app.py` | Generated fictional SQLite database per browser session | Temporary; resettable from the sidebar |
| `personal_app.py` | `DATABASE_URL` from the environment, local `.env` or Streamlit secrets | Persistent; owned by the single user |

## Public sandbox

```sh
streamlit run streamlit_app.py
```

This is also the main file used by the
[public deployment](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app).
It does not resolve a personal database URL, even when one is configured on the
host. Each browser session receives a separately generated database and cache
identity. Edits survive reruns within the session. **Reset demo** discards its
edits and generates a fresh sandbox without affecting other sessions.

The demo uses the same schema, writers and calculation rules as the personal
application. Its banner identifies fictional data and temporary changes.
The database stays in memory and is released when Streamlit expires the session.
Reconnecting after session expiration starts a new dataset; it is not a place
to store personal workouts. Streamlit's
[session-scoped resource cache](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
owns resource cleanup.

Existing Cloud deployments continue using `streamlit_app.py`; ordinary GitHub
redeployment switches them to the sandbox. Remove an obsolete personal database
secret from the Cloud settings after verifying the deployed demo. The application
does not need it and does not modify that database.

## Persistent personal app

Configure your database using [local setup](getting-started.md), then run:

```sh
streamlit run personal_app.py
```

This is the command to use for your actual training records. Switching entry
points does not copy, clear or migrate the personal database. The app remains
single-user without accounts. Docker Compose uses this persistent entry point
with its own generated PostgreSQL demo and named volume, as described in the
[Docker guide](docker.md).
