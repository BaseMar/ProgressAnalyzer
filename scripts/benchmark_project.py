"""Measure real Streamlit entry-point reruns and save synthetic reference outputs.

Default: disposable in-memory SQLite. --live uses the configured application
database in read-only transactions; it never applies migrations or seeds data.
"""

import argparse
import json
import logging
import os
import platform
import statistics
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from importlib import import_module, metadata
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlalchemy import event, inspect
from streamlit.testing.v1 import AppTest

from scripts.baseline_fixture import AS_OF, create_fixture
from scripts.baseline_snapshot import (
    capture_snapshot,
    digest,
    load_input,
    normalized,
    snapshot_reference,
)


class ReadOnlyProbe:
    """Count executed SQL, reject writes and require database-level read-only mode."""

    def __init__(self, engine):
        self.engine = engine
        self.enabled = False
        self.statements = []
        self.started = {}

    def begin(self, connection):
        statement = (
            "SET TRANSACTION READ ONLY"
            if self.engine.dialect.name == "postgresql"
            else "PRAGMA query_only=ON"
        )
        connection.exec_driver_sql(statement)

    def before(self, connection, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.split())
        upper = sql.upper()
        control = upper in ("SET TRANSACTION READ ONLY", "PRAGMA QUERY_ONLY=ON")
        readable = (
            upper.startswith(("SELECT ", "SHOW ", "PRAGMA MAIN.", "PRAGMA TEMP."))
            or upper == "PRAGMA QUERY_ONLY"
        )
        if not control and not readable:
            raise RuntimeError("Baseline rendering attempted a non-read-only SQL statement")
        if self.enabled and not control:
            self.started[id(context)] = (perf_counter(), sql)

    def after(self, connection, cursor, statement, parameters, context, executemany):
        started = self.started.pop(id(context), None)
        if started:
            self.statements.append((started[1], (perf_counter() - started[0]) * 1000))

    def __enter__(self):
        event.listen(self.engine, "begin", self.begin)
        event.listen(self.engine, "before_cursor_execute", self.before)
        event.listen(self.engine, "after_cursor_execute", self.after)
        return self

    def __exit__(self, *args):
        event.remove(self.engine, "begin", self.begin)
        event.remove(self.engine, "before_cursor_execute", self.before)
        event.remove(self.engine, "after_cursor_execute", self.after)

    def measure(self, action):
        self.statements = []
        self.enabled = True
        started = perf_counter()
        try:
            action()
        finally:
            elapsed = (perf_counter() - started) * 1000
            self.enabled = False
        counts = {}
        for sql, duration in self.statements:
            row = counts.setdefault(sql, dict(count=0, total_ms=0.0))
            row["count"] += 1
            row["total_ms"] += duration
        return dict(
            elapsed_ms=round(elapsed, 3),
            sql_count=len(self.statements),
            sql_ms=round(sum(duration for _, duration in self.statements), 3),
            repeated_sql=[
                dict(statement=sql, count=row["count"], total_ms=round(row["total_ms"], 3))
                for sql, row in sorted(
                    counts.items(), key=lambda pair: pair[1]["count"], reverse=True
                )[:5]
            ],
        )


@contextmanager
def fixed_clock(as_of):
    class ReferenceDate(date):
        @classmethod
        def today(cls):
            return as_of

        @classmethod
        def fromisoformat(cls, value):
            return date.fromisoformat(value)

    names = (
        "ui.overview_view",
        "ui.next_workout_view",
        "ui.analysis_view",
        "ui.history_view",
        "ui.training_plan_view",
        "ui.plan_adherence_view",
        "ui.plan_schedule_view",
        "ui.utils.history_period",
        "db.plan_adherence",
    )
    with ExitStack() as stack:
        for name in names:
            module = import_module(name)
            if hasattr(module, "date"):
                stack.enter_context(patch.object(module, "date", ReferenceDate))
        yield


PROTECTED_TABLES = (
    "exercises",
    "workout_sessions",
    "workout_exercises",
    "workout_sets",
    "body_measurements",
    "body_composition",
    "exercise_muscle_map",
    "training_plans",
    "training_plan_versions",
    "training_plan_days",
    "training_plan_exercises",
    "training_plan_session_links",
    "training_plan_exercise_matches",
    "workout_set_classifications",
    "workout_set_loads",
    "training_plan_progression",
    "training_plan_exercise_lineage",
    "recommendation_starting_loads",
    "exercise_history_load_settings",
    "schema_migrations",
)


def database_fingerprint(engine):
    result = {}
    with engine.connect() as connection:
        existing = set(inspect(connection).get_table_names())
        quote = connection.dialect.identifier_preparer.quote
        for table in sorted(existing.intersection(PROTECTED_TABLES)):
            rows = connection.exec_driver_sql(f"SELECT * FROM {quote(table)}").all()
            values = sorted(
                (normalized(list(row)) for row in rows),
                key=lambda row: json.dumps(row, sort_keys=True),
            )
            result[table] = dict(rows=len(rows), sha256=digest(values))
    return result


def app_output(app):
    return digest(
        dict(
            metrics=[(item.label, item.value, item.delta) for item in app.metric],
            notes=[item.value for item in app.code],
            recommendations=[
                item.value for item in app.markdown if 'class="recommendation-list"' in item.value
            ],
            tables=[
                item.value.to_json(orient="split", date_format="iso", double_precision=8)
                for item in app.dataframe
            ],
        )
    )


def check_app(app):
    if app.exception or app.error:
        raise RuntimeError(
            f"Baseline page failed: exceptions={len(app.exception)}, errors={len(app.error)}"
        )


def render_case(probe, plan_id, state, runs):
    st.cache_data.clear()
    app = AppTest.from_file(str(ROOT / "personal_app.py"), default_timeout=120)
    for key, value in dict(active_plan_id=plan_id, adherence_plan=plan_id, **state).items():
        app.session_state[key] = value
    cold = probe.measure(app.run)
    check_app(app)
    expected = app_output(app)
    warm = []
    for _ in range(runs):
        warm.append(probe.measure(app.run))
        check_app(app)
        if app_output(app) != expected:
            raise AssertionError("Warm rerun changed displayed results")
    return dict(
        cold=cold,
        warm=warm,
        warm_median_ms=round(statistics.median(row["elapsed_ms"] for row in warm), 3),
        output_sha256=expected,
    )


CASE_NAMES = (
    "overview",
    "analysis_plan_progress",
    "analysis_recorded_exercises",
    "analysis_consistency",
    "analysis_muscle_map",
    "analysis_set_allocation",
    "analysis_measurements",
    "plan",
    "history",
    "workout_switch",
)


def render_benchmarks(probe, plan, as_of, runs, selected=None):
    cases = {
        "overview": dict(nav_selected="Overview"),
        "analysis_plan_progress": dict(
            nav_selected="Analysis", analysis_question="Exercise progress"
        ),
        "analysis_recorded_exercises": dict(
            nav_selected="Analysis",
            analysis_question="Exercise progress",
        ),
        "analysis_consistency": dict(nav_selected="Analysis", analysis_question="Plan consistency"),
        "analysis_muscle_map": dict(
            nav_selected="Analysis", analysis_question="Muscle distribution"
        ),
        "analysis_set_allocation": dict(
            nav_selected="Analysis",
            analysis_question="Muscle distribution",
            analysis_muscle_view="Set allocation",
        ),
        "analysis_measurements": dict(
            nav_selected="Analysis", analysis_question="Body measurements"
        ),
        "plan": dict(nav_selected="Plan"),
        "history": dict(nav_selected="History"),
    }
    results = {}
    for name, state in cases.items():
        if selected and name not in selected:
            continue
        if state["nav_selected"] == "Analysis":
            state["analysis_month"] = "All time"
        print(f"Measuring {name}", flush=True)
        results[name] = render_case(probe, plan.plan_id, state, runs)
    if selected and "workout_switch" not in selected:
        return results
    from db.plan_schedule import load_scheduled_workouts

    slots = sorted(
        (
            slot
            for slot in load_scheduled_workouts(
                probe.engine, plan.plan_id, as_of, as_of + timedelta(days=28)
            )
            if slot.session_id is None
        ),
        key=lambda slot: (slot.scheduled_date, slot.position, slot.day_id),
    )
    if len(slots) < 2:
        raise RuntimeError("Workout switching requires two upcoming unlinked workouts")
    app = AppTest.from_file(str(ROOT / "personal_app.py"), default_timeout=120)
    app.session_state["active_plan_id"] = plan.plan_id
    app.session_state["adherence_plan"] = plan.plan_id
    app.run()
    check_app(app)
    switches = []
    for index in range(runs):
        slot = slots[(index + 1) % 2]
        target = f"{slot.day_id}:{slot.scheduled_date}"
        selector = app.selectbox(key=f"next_workout_{plan.plan_id}")
        if selector.value == target:
            raise AssertionError("Workout-switch sample must change the selected workout")
        switches.append(probe.measure(lambda: selector.select(target).run()))
        check_app(app)
    results["workout_switch"] = dict(
        warm=switches,
        warm_median_ms=round(statistics.median(row["elapsed_ms"] for row in switches), 3),
    )
    return results


def calculation_benchmarks(engine, plan, as_of, runs):
    from db.plan_adherence import load_plan_performance
    from db.training_plans import load_training_plan_versions
    from metrics.exercise_metrics import compute_exercise_metrics
    from metrics.measurement_timeline import measurement_timeline
    from metrics.muscle_volume import weekly_plan_allocation
    from metrics.plan_adherence import compute_plan_adherence
    from metrics.plan_performance import compute_plan_performance
    from metrics.training_insights import compute_training_insights

    input_data, _ = load_input(engine)
    history = load_plan_performance(engine, plan.plan_id, as_of - timedelta(days=27), as_of)
    settings = {
        version.version_id: version.draft.progression
        for version in load_training_plan_versions(engine, plan.plan_id)
    }
    cases = dict(
        exercise_metrics=lambda: compute_exercise_metrics(input_data),
        plan_adherence=lambda: compute_plan_adherence(
            history, as_of=as_of, settings_by_version=settings
        ),
        plan_performance=lambda: compute_plan_performance(
            history, as_of=as_of, settings_by_version=settings
        ),
        training_insights=lambda: compute_training_insights(
            history, as_of=as_of, settings_by_version=settings
        ),
        muscle_allocation=lambda: weekly_plan_allocation(plan.draft, input_data),
        measurements=lambda: measurement_timeline(input_data),
    )
    result = {}
    for name, action in cases.items():
        samples = []
        for _ in range(runs):
            started = perf_counter()
            action()
            samples.append(round((perf_counter() - started) * 1000, 3))
        result[name] = dict(samples_ms=samples, median_ms=round(statistics.median(samples), 3))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Read-only measurements against the configured application database",
    )
    parser.add_argument("--runs", type=int, default=3, help="Warm samples per case")
    parser.add_argument(
        "--case",
        action="append",
        choices=CASE_NAMES,
        help="Measure only named render cases; may be repeated",
    )
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/baseline/results.json")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    for name in (
        "streamlit",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner_utils.script_run_context",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)
    if args.live:
        from db.connection import get_engine
        from db.training_plans import load_training_plans

        engine = get_engine()
        if engine.dialect.name != "postgresql":
            raise RuntimeError("--live requires PostgreSQL read-only transactions")
        as_of = date.today()
    else:
        engine, plan = create_fixture()
        as_of = AS_OF
    try:
        with (
            ReadOnlyProbe(engine) as probe,
            patch("data_manager.get_engine", return_value=engine),
            fixed_clock(as_of),
        ):
            with engine.connect() as connection:
                if args.live:
                    read_only = (
                        connection.exec_driver_sql("SHOW transaction_read_only").scalar_one()
                        == "on"
                    )
                else:
                    read_only = connection.exec_driver_sql("PRAGMA query_only").scalar_one() == 1
                if not read_only:
                    raise AssertionError("Database-level read-only mode was not enabled")
            before = database_fingerprint(engine)
            if args.live:
                plans = load_training_plans(engine)
                plan = max(plans, key=lambda item: item.version_id)
            snapshot = None if args.live else capture_snapshot(engine, plan)
            results = dict(
                mode="live_postgresql" if args.live else "synthetic_sqlite",
                as_of=as_of.isoformat(),
                analysis_period="All time",
                commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                working_tree_dirty=bool(
                    subprocess.check_output(
                        ["git", "status", "--porcelain"], cwd=ROOT, text=True
                    ).strip()
                ),
                environment=dict(
                    python=platform.python_version(),
                    streamlit=metadata.version("streamlit"),
                    sqlalchemy=metadata.version("sqlalchemy"),
                    pandas=metadata.version("pandas"),
                    numpy=metadata.version("numpy"),
                    plotly=metadata.version("plotly"),
                    platform=platform.system(),
                    machine=platform.machine(),
                    logical_cpus=os.cpu_count(),
                ),
                fixture_counts={table: row["rows"] for table, row in before.items()},
                database_read_only_verified=read_only,
                renders=render_benchmarks(probe, plan, as_of, args.runs, args.case),
                calculations=calculation_benchmarks(engine, plan, as_of, args.runs),
            )
            after = database_fingerprint(engine)
            if before != after:
                raise AssertionError("Database contents changed during baseline measurement")
            results["database_unchanged"] = True
            if snapshot is not None:
                results["reference"] = snapshot_reference(snapshot)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.with_name("snapshot.json").write_text(
                    json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
                )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"Baseline saved: {args.output}", flush=True)
    finally:
        st.cache_data.clear()
        engine.dispose()


if __name__ == "__main__":
    main()
