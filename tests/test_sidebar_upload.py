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


def test_parse_txt_reads_compact_numbered_workout(monkeypatch):
    upload = _upload()
    warnings = []

    monkeypatch.setattr(
        "ui.sidebar_upload.st.sidebar",
        SimpleNamespace(warning=warnings.append),
    )

    parsed = upload._parse_txt(
        "Godzina 15:35-16:50\n"
        "1. Incline Dumbbell Press\n"
        "10x24/10x24/6x26\n"
        "RIR 2/2/0\n\n"
        "2. Pec Deck\n"
        "9x75/12x65/10x65\n"
        "RIR 1/0/0\n\n"
        "3. Lat Pulldown\n"
        "12x70/10x70/11x70\n"
        "RIR 1/0/0\n\n"
        "4. T-Bar Row\n"
        "8x50/8x50/8x50\n"
        "RIR 1/1/1\n\n"
        "5. Ez Barbell Curl\n"
        "12x35/10x35/11x35\n"
        "RIR 1/0/0\n\n"
        "6. Military Press\n"
        "6x40/6x45\n"
        "RIR 2/1\n\n"
        "7. Overhead Extension\n"
        "15x35/15x40/10x50\n"
        "RIR 2/1/0\n"
    )

    assert [exercise["name"] for exercise in parsed] == [
        "Incline Dumbbell Press",
        "Pec Deck",
        "Lat Pulldown",
        "T-Bar Row",
        "Ez Barbell Curl",
        "Military Press",
        "Overhead Extension",
    ]
    assert sum(len(exercise["sets"]) for exercise in parsed) == 20
    assert parsed[0]["sets"] == [
        {"reps": 10, "weight": 24.0, "rir": 2},
        {"reps": 10, "weight": 24.0, "rir": 2},
        {"reps": 6, "weight": 26.0, "rir": 0},
    ]
    assert parsed[-1]["sets"][-1] == {"reps": 10, "weight": 50.0, "rir": 0}
    assert warnings == []


def test_parse_txt_keeps_sets_when_rir_is_missing(monkeypatch):
    upload = _upload()
    warnings = []

    monkeypatch.setattr(
        "ui.sidebar_upload.st.sidebar",
        SimpleNamespace(warning=warnings.append),
    )

    parsed = upload._parse_txt(
        "1) Bench Press\n"
        "Serie: 10 x 100 kg, 8x110, 6x115\n"
        "RIR: 2/1\n"
    )

    assert parsed == [
        {
            "name": "Bench Press",
            "sets": [
                {"reps": 10, "weight": 100.0, "rir": 2},
                {"reps": 8, "weight": 110.0, "rir": 1},
                {"reps": 6, "weight": 115.0, "rir": None},
            ],
        }
    ]
    assert len(warnings) == 1


def test_parse_txt_reads_inline_numbered_exercises(monkeypatch):
    upload = _upload()
    warnings = []

    monkeypatch.setattr(
        "ui.sidebar_upload.st.sidebar",
        SimpleNamespace(warning=warnings.append),
    )

    parsed = upload._parse_txt(
        "1) Bench Press: 10x100 RIR 2 / 8x110 RIR 1\n"
        "2 - Row\n"
        "Sets: 12*60kg, 10 @ 65, 8 x 67,5 kg\n"
        "RIR = 3 / 2 / 1\n"
    )

    assert parsed == [
        {
            "name": "Bench Press",
            "sets": [
                {"reps": 10, "weight": 100.0, "rir": 2},
                {"reps": 8, "weight": 110.0, "rir": 1},
            ],
        },
        {
            "name": "Row",
            "sets": [
                {"reps": 12, "weight": 60.0, "rir": 3},
                {"reps": 10, "weight": 65.0, "rir": 2},
                {"reps": 8, "weight": 67.5, "rir": 1},
            ],
        },
    ]
    assert warnings == []


def test_parse_txt_reads_unnumbered_inline_and_multiline_blocks(monkeypatch):
    upload = _upload()
    warnings = []

    monkeypatch.setattr(
        "ui.sidebar_upload.st.sidebar",
        SimpleNamespace(warning=warnings.append),
    )

    parsed = upload._parse_txt(
        "Bench Press: 10x100/8x110 RIR 2/1\n\n"
        "Row\n"
        "12x60\n"
        "RIR 3\n"
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
    assert upload._parse_time_range("Godzina 15:35-16:50") == (
        time(15, 35),
        time(16, 50),
    )
    assert upload._parse_time_range("Godz. 15.35 do 16.50") == (
        time(15, 35),
        time(16, 50),
    )
    assert upload._parse_time_range("15:35-16:50") == (
        time(15, 35),
        time(16, 50),
    )
    assert upload._parse_time_range("missing") == (None, None)
