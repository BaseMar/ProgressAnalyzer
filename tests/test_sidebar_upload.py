from datetime import time
from types import SimpleNamespace

import pandas as pd

from ui.sidebar_upload import SidebarUpload


def _upload() -> SidebarUpload:
    return object.__new__(SidebarUpload)


def test_similarity_score_handles_equal_empty_and_partial_strings():
    upload = _upload()

    assert upload._similarity_score("bench", "bench") == 1.0
    assert upload._similarity_score("", "") == 1.0
    assert upload._similarity_score("bench", "bunch") == 0.8


def test_find_similar_exercises_uses_normalized_names():
    upload = _upload()
    exercises_df = pd.DataFrame(
        [
            {"exercise_name": "Bench Press"},
            {"exercise_name": "Romanian Deadlift"},
            {"exercise_name": "Squat"},
        ]
    )

    similar = upload._find_similar_exercises("bench", exercises_df)

    assert [row.exercise_name for row in similar] == ["Bench Press"]


def test_parse_txt_reads_sets_and_rir_values(monkeypatch):
    upload = _upload()
    warnings = []

    monkeypatch.setattr(
        "ui.sidebar_upload.st.sidebar",
        SimpleNamespace(warning=warnings.append),
    )

    parsed = upload._parse_txt(
        "1. Bench Press\n"
        "10x100 / 8x110\n"
        "RIR: 2 / 1\n"
        "2. Row\n"
        "12x60\n"
        "RIR: 3\n"
    )

    assert parsed == [
        {
            "name": "Bench Press",
            "sets": [
                {"reps": 10, "weight": 100.0, "rir": 2},
                {"reps": 8, "weight": 110.0, "rir": 1},
            ],
        },
        {"name": "Row", "sets": [{"reps": 12, "weight": 60.0, "rir": 3}]},
    ]
    assert warnings == []


def test_parse_time_range_supports_hyphen_and_unicode_dashes():
    upload = _upload()

    assert upload._parse_time_range("Godzina: 10:30 - 12:45") == (
        time(10, 30),
        time(12, 45),
    )
    assert upload._parse_time_range("Godzina: 10:30 \u2013 12:45") == (
        time(10, 30),
        time(12, 45),
    )
    assert upload._parse_time_range("missing") == (None, None)
