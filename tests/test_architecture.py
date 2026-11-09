"""Protect the boundaries between calculations, persistence and presentation."""

import ast
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from metrics.utils.dates import to_date

ROOT = Path(__file__).resolve().parents[1]


def imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_models_and_metrics_do_not_depend_on_storage_or_presentation():
    forbidden = {"db", "ui", "services", "streamlit", "data_manager", "data_loader"}
    violations = {
        str(path.relative_to(ROOT)): sorted(forbidden.intersection(imports(path)))
        for directory in ("models", "metrics")
        for path in (ROOT / directory).rglob("*.py")
        if forbidden.intersection(imports(path))
    }
    assert not violations


def test_row_mapping_does_not_access_storage_or_application_services():
    assert not {
        "db",
        "ui",
        "services",
        "streamlit",
        "data_manager",
        "data_loader",
        "sqlalchemy",
    }.intersection(imports(ROOT / "mapper.py"))


@pytest.mark.parametrize(
    "value",
    [
        date(2026, 11, 9),
        datetime(2026, 11, 9, 15, 30),
        pd.Timestamp("2026-11-09T15:30:00"),
        "2026-11-09",
        "2026-11-09T15:30:00",
    ],
)
def test_shared_date_utility_retains_supported_record_formats(value):
    assert to_date(value) == date(2026, 11, 9)


def test_shared_date_utility_rejects_values_that_are_not_dates():
    with pytest.raises(TypeError, match="Unsupported date value"):
        to_date(42)
