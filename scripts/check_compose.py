"""Build and exercise Compose in an isolated project, including persistent-volume reuse."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]

CHECK_APP = """
import os
from pathlib import Path
from streamlit.testing.v1 import AppTest
assert os.getuid() == 10001
assert not any(Path(p).exists() for p in ('.env', '.streamlit/secrets.toml', '.git', '.venv', 'backups'))
assert Path('ui/wzorzec/human_body.png').is_file()
for page in ('Overview', 'Analysis', 'Plan', 'History'):
    app = AppTest.from_file('streamlit_app.py', default_timeout=60)
    app.session_state['nav_selected'] = page
    app.run()
    assert not app.exception and not app.error, page
    if page == 'Analysis':
        app.selectbox(key='analysis_question').select('Muscle distribution').run()
        assert not app.exception and not app.error, 'Muscle distribution'
        assert app.get('iframe')[0].proto.alt == 'Muscle allocation compared with the training plan'
"""

WRITE_RECORD = """
from datetime import date
from data_manager import DataManager
manager = DataManager()
assert manager.add_workout_session(date.today(), 'Compose persistence acceptance', [{
    'name': 'Barbell Bench Press', 'sets': [{'reps': 8, 'weight': 60.0, 'rir': 2}],
}])
"""

SNAPSHOT = """
import hashlib
import json
from sqlalchemy import inspect
from db.connection import get_engine
engine = get_engine()
tables = sorted(inspect(engine).get_table_names())
assert len(tables) == 20
counts, fingerprints = {}, {}
with engine.connect() as connection:
    for table in tables:
        name = connection.dialect.identifier_preparer.quote(table)
        rows = connection.exec_driver_sql('SELECT * FROM ' + name).all()
        records = sorted(json.dumps(tuple(row), default=str) for row in rows)
        counts[table] = len(records)
        fingerprints[table] = hashlib.sha256(json.dumps(records).encode()).hexdigest()
assert counts['exercises'] == 9 and counts['training_plans'] == 1
assert counts['schema_migrations'] == 9 and counts['workout_sets'] >= 300
print(json.dumps({'counts': counts, 'fingerprints': fingerprints}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18501, help="Temporary localhost HTTP port")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535")
    project = "progress-analyzer-check-" + uuid4().hex[:12]
    environment = {**os.environ, "DEMO_PORT": str(args.port)}
    prefix = ["docker", "compose", "--project-name", project]

    def compose(*arguments, code=None, capture=False):
        return subprocess.run(
            prefix + list(arguments),
            cwd=ROOT,
            env=environment,
            input=code,
            text=True,
            capture_output=capture,
            check=True,
        )

    def execute(code):
        result = compose(
            "exec",
            "-T",
            "app",
            "python",
            "-W",
            "error::DeprecationWarning",
            "-",
            code=code,
            capture=True,
        )
        return json.loads(result.stdout.strip().splitlines()[-1])

    def healthy():
        with urlopen(f"http://127.0.0.1:{args.port}/_stcore/health", timeout=10) as response:
            assert response.status == 200

    try:
        compose("config", "--quiet")
        compose("up", "--build", "--wait", "--wait-timeout", "240")
        healthy()
        initial = execute(CHECK_APP + SNAPSHOT)
        written = execute(WRITE_RECORD + SNAPSHOT)
        assert written["counts"]["workout_sessions"] == initial["counts"]["workout_sessions"] + 1
        assert written["counts"]["workout_sets"] == initial["counts"]["workout_sets"] + 1
        # Removing the containers/network retains this test project's named volume.
        compose("down")
        compose("up", "--wait", "--wait-timeout", "180")
        healthy()
        after = execute(CHECK_APP + SNAPSHOT)
        assert after == written, "Container recreation changed or reseeded stored records"
        print(
            json.dumps(
                dict(
                    passed=True,
                    four_pages_before_and_after_restart=True,
                    application_runs_without_root=True,
                    private_files_excluded=True,
                    tables=20,
                    persisted_after_container_recreation=True,
                    demo_not_reseeded=True,
                ),
                indent=2,
            )
        )
    except (subprocess.SubprocessError, OSError, AssertionError, ValueError) as error:
        print(str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stdout or "", file=sys.stderr)
            print(error.stderr or "", file=sys.stderr)
        subprocess.run(prefix + ["logs", "--no-color"], cwd=ROOT, env=environment, check=False)
        raise
    finally:
        # The random project name is created here; the user's demo volume is untouched.
        subprocess.run(
            prefix + ["down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=environment,
            check=True,
        )


if __name__ == "__main__":
    main()
