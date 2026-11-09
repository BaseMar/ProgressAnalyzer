"""Freeze current semantic results before changing loading, caching and architecture."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.baseline_fixture import AS_OF, create_fixture
from scripts.baseline_snapshot import capture_snapshot, digest, snapshot_reference
from scripts.benchmark_project import ReadOnlyProbe, database_fingerprint

REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures/project_baseline.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def baseline():
    engine, plan = create_fixture()
    try:
        yield engine, plan, capture_snapshot(engine, plan)
    finally:
        engine.dispose()


@pytest.mark.parametrize("section", sorted(REFERENCE["sections"]))
def test_current_outputs_match_preoptimization_reference(baseline, section):
    snapshot = baseline[2]
    assert snapshot["fixture"] == REFERENCE["fixture"]
    assert digest(snapshot[section]) == REFERENCE["sections"][section], (
        f"{section} changed. Inspect the full synthetic snapshot before accepting a new reference."
    )


def test_reference_has_reviewable_starting_load_and_deload_examples(baseline):
    snapshot = baseline[2]
    assert snapshot_reference(snapshot)["examples"] == REFERENCE["examples"]
    bench, row, pullup, curl, hang, plank = snapshot["recommendations"]["Upper A"]["exercises"]
    assert [g[0] for g in bench["goals"]] == [
        62.5
    ] * 3  # Latest ordinary unlinked history, not the future 200 kg entry.
    assert bench["rir"] == 3 and bench["action"] == "maintain"
    assert [g[0] for g in row["goals"]] == [
        70.0
    ] * 4  # The changed set count retains recorded settings.
    assert all(g[0] == 0.0 and g[4] == "bodyweight" for g in pullup["goals"])
    assert [g[0] for g in curl["goals"]] == [12.0, 10.0, 10.0]
    assert hang["goals"][0][1] == 40 and plank["goals"][0][1] == 40
    phases = snapshot["phase_cases"]
    assert phases["ordinary_increase"]["exercises"][0]["action"] == "increase_weight"
    assert phases["deload"]["exercises"][0]["goals"][0][:3] == [40.0, 10, 10]
    assert phases["return_after_deload"]["exercises"][0]["reason"] == "resume_after_deload"


def test_snapshot_cutoff_does_not_drift_with_a_later_wall_clock(baseline):
    engine, plan, snapshot = baseline
    with patch("db.plan_adherence.date") as clock:
        clock.today.return_value = AS_OF.replace(year=2027)
        assert snapshot_reference(capture_snapshot(engine, plan)) == snapshot_reference(snapshot)


def test_measurement_probe_rejects_writes_and_preserves_fixture_data(baseline):
    engine = baseline[0]
    with ReadOnlyProbe(engine) as probe:
        before = database_fingerprint(engine)
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA query_only").scalar_one() == 1
            measurement = probe.measure(lambda: connection.exec_driver_sql("SELECT 1").scalar_one())
            assert measurement["sql_count"] == 1
            with pytest.raises(RuntimeError, match="non-read-only"):
                connection.exec_driver_sql("DELETE FROM workout_sets")
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                connection.connection.driver_connection.execute("DELETE FROM workout_sets")
        assert database_fingerprint(engine) == before
