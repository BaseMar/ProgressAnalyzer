# Docker Compose demo

Compose runs the dashboard and PostgreSQL together, creates the schema and
generates fictional example data on the first start. Python and PostgreSQL
do not need to be installed on the host for this route.

## Requirements and first start

Install and start Docker with the Compose v2 plugin. On Windows, use
[Docker Desktop with Linux containers](https://docs.docker.com/desktop/setup/install/windows-install/).
On Linux, use [Docker Engine and the Compose plugin](https://docs.docker.com/compose/install/linux/).
`docker compose version` should succeed before starting the demo.

From the cloned repository root, in Git Bash, PowerShell or a Linux/macOS shell:

```sh
docker compose up --build --wait
```

Open **http://localhost:8501** after the command succeeds. The first build
downloads the base images and installs the pinned runtime dependencies.
`--wait` leaves the services running in the background after they become healthy.

Compose waits for PostgreSQL's TCP health check before starting the app.
The app container's preparatory launcher creates an empty database's schema
and synthetic demo. Streamlit starts after this succeeds, and its own HTTP
health check reports readiness. These dependency rules follow
[Docker's startup-order guidance](https://docs.docker.com/compose/how-tos/startup-order/).

## Data ownership and subsequent starts

The database lives in the project's named `demo-postgres` volume. The app image
runs as a regular user. PostgreSQL has no host port; the dashboard is published
on the host's loopback interface only.

The [Compose configuration](../compose.yaml) supplies its own internal database
URL and fixed local-demo credentials. The host's `DATABASE_URL` does not select
this container database. Local `.env`, Streamlit secrets, `.venv`, Git metadata,
SQLite databases and backups are excluded from the application build. No host
source or personal-data directories are mounted into either container.

On subsequent starts, the launcher keeps existing records, applies any pending
known migrations and starts the app. It does not regenerate the demo or reset
edits. The demo's dates remain anchored to its initial creation. An incomplete
or unrecognized database schema stops startup rather than being overwritten.

Stop and remove the containers while retaining saved demo data:

```sh
docker compose down
```

Start again, reusing the saved data:

```sh
docker compose up --build --wait
```

To intentionally discard this Compose project's saved demo data and generate
a fresh dataset:

```sh
docker compose down --volumes
docker compose up --build --wait
```

The [PostgreSQL 16 image](https://hub.docker.com/_/postgres) stores its cluster
in `/var/lib/postgresql/data`, which is the persistent volume's container path.

## Port conflicts and logs

If a locally running Streamlit instance occupies port 8501, stop it with Ctrl+C
or choose another host port.

Git Bash / Bash:

```bash
DEMO_PORT=8502 docker compose up --build --wait
```

PowerShell:

```powershell
$env:DEMO_PORT = "8502"
docker compose up --build --wait
```

Then open http://localhost:8502. The same optional `DEMO_PORT` setting can be
stored in local `.env`; the container database URL remains independent of it.

Inspect status and startup logs:

```sh
docker compose ps
docker compose logs --tail=100 app db
```

Changing PostgreSQL major versions is a separate database-upgrade task. The
configuration retains PostgreSQL 16 across ordinary application rebuilds.

## Verification

The [Tests workflow](../.github/workflows/tests.yml) has a separate Docker
Compose acceptance job. It builds the real image, waits for both health checks
and renders all four application pages inside the runtime image. It also
checks that the app runs without root and that private host files are absent.

The job saves a synthetic workout, removes and recreates the containers while
keeping the volume, then compares fingerprints of all twenty tables. The
record must survive and the demo must not be seeded again. The workflow uses
a deliberately invalid host `.env` URL to verify that container settings select
the internal database instead.

With Docker and Python available locally, run the same acceptance check:

```sh
python scripts/check_compose.py
```

The check creates a randomly named temporary Compose project, uses port 18501
(override with `--port`) and removes only its own containers and volume afterward.
It leaves the normal demo project's data intact. On hosts without Docker,
the Python suite can still verify initialization/restart behavior with SQLite;
the real container checks run in CI.
