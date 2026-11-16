"""Automatic entry conventions and reversible, conservative history normalization."""

from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import event, func, select
from streamlit.testing.v1 import AppTest

from db.exercise_history_load_settings import confirm_legacy_body_mass_history
from db.load_profiles import originals, profiles
from db.set_loads import loads
from db.workout_sessions import save_workout_session
from mapper import map_workout_set
from metrics.exercise_metrics import compute_exercise_metrics
from metrics.input import MetricsInput
from metrics.load_profiles import resolve_exercise_load_profile, resolve_recorded_load
from models.load_profile import ExerciseLoadProfile
from models.set_load import SetLoad
from test_bodyweight_entry import entry_data as entry_data
from test_plan_schedule import schedule_data as schedule_data
from test_workout_template import parser as parser

DAY = date(2026, 2, 15)


def raw_entry(manager, eid, weight, *, day=DAY, load=None):
    save_workout_session(
        manager.engine,
        day,
        "Historical entry",
        [
            {
                "name": "Unused when ID is supplied",
                "exercise_id": eid,
                "sets": [
                    {"reps": 8, "weight": weight, "rir": 2, **({"load": load} if load else {})}
                ],
            }
        ],
    )


@pytest.mark.parametrize(
    "name,kind",
    [
        ("Bench Press", "external"),
        ("Dead hang", "bodyweight"),
        ("Plank", "bodyweight"),
        ("Pull-up", "bodyweight"),
        ("Chest Dip", "bodyweight"),
        ("Machine Chest Dip", "external"),
        ("Assisted dips", "assisted_bodyweight"),
        ("Pompki", "bodyweight"),
    ],
)
def test_catalog_defaults(name, kind):
    assert resolve_exercise_load_profile(1, name).load_type == kind


def test_profile_precedence_and_confirmed_old_body_mass():
    saved = ExerciseLoadProfile(1, "external", "external", "external", "user")
    assert (
        resolve_exercise_load_profile(1, "Pull-up", saved=saved, history=("bodyweight",)) == saved
    )
    assert (
        resolve_exercise_load_profile(1, "Custom exercise", history=("bodyweight",)).load_type
        == "bodyweight"
    )
    profile = resolve_exercise_load_profile(1, "Pull-up", body_mass_confirmed=True)
    assert resolve_recorded_load(profile, 80, body_mass=90) == SetLoad("bodyweight", 0, 80)
    assert resolve_recorded_load(profile, 5, body_mass=80, mode="additional") == SetLoad(
        "bodyweight", 5, 80
    )


def test_ambiguous_old_bodyweight_does_not_use_the_size_of_the_number():
    profile = resolve_exercise_load_profile(1, "Pull-up")
    assert resolve_recorded_load(profile, 80, body_mass=80, mode="unknown") is None
    assert resolve_recorded_load(profile, 5, body_mass=80, mode="unknown") is None
    assert resolve_recorded_load(profile, 0, body_mass=80, mode="unknown") == SetLoad(
        "bodyweight", 0, 80
    )
    assisted = resolve_exercise_load_profile(1, "Assisted Pull-up")
    assert resolve_recorded_load(assisted, 60, body_mass=80, mode="total") is None


def test_normalization_archives_originals_preserves_explicit_and_future_data_and_is_idempotent(
    entry_data,
):
    raw_entry(entry_data, 1, 60)
    raw_entry(entry_data, 1, 65, day=date(2026, 2, 16), load=SetLoad("external", 65))
    raw_entry(entry_data, 1, 100, day=date(2099, 1, 1))
    raw_entry(entry_data, 2, 0)
    raw_entry(entry_data, 3, 80)
    raw_entry(entry_data, 4, 30)
    confirm_legacy_body_mass_history(entry_data.engine, 3)
    before = entry_data.load_sets_raw()
    audit = entry_data.audit_load_history()
    assert (audit["convertible"], audit["unresolved"]) == (3, 1)
    with entry_data.engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(originals)).scalar_one() == 0
    result = entry_data.normalize_load_history()
    assert (result["converted"], result["unresolved"]) == (3, 1)
    rows = entry_data.load_sets_ui()
    pullup = rows.loc[rows.exercise_name == "Pull-up"].iloc[0]
    assert (pullup.weight, pullup.body_mass_kg, pullup.load_type) == (0, 80, "bodyweight")
    external = rows.loc[(rows.exercise_name == "Bench Press") & (rows.weight == 60)].iloc[0]
    assert external.load_type == "external"
    unresolved = rows.loc[rows.exercise_name == "Assisted dips"].iloc[0]
    assert unresolved.weight == 30 and unresolved.load_type is None
    with entry_data.engine.connect() as conn:
        archive = conn.execute(select(originals)).mappings().all()
        assert sorted(row["weight"] for row in archive) == [0, 60, 80]
        assert conn.execute(select(func.count()).select_from(loads)).scalar_one() == 4
    assert len(entry_data.load_sets_raw()) == len(before)
    assert entry_data.normalize_load_history()["converted"] == 0


def test_normalization_failure_rolls_back_profiles_archives_weights_and_snapshots(entry_data):
    raw_entry(entry_data, 1, 60)

    def fail(_, __, statement, ___, ____, _____):
        if statement.startswith("INSERT INTO workout_set_loads"):
            raise RuntimeError("Synthetic snapshot failure")

    event.listen(entry_data.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic snapshot"):
            entry_data.normalize_load_history()
    finally:
        event.remove(entry_data.engine, "before_cursor_execute", fail)
    with entry_data.engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(originals)).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(profiles)).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(loads)).scalar_one() == 0
    assert entry_data.load_sets_raw().iloc[0].weight == 60


def test_original_can_be_restored_without_overwriting_a_later_correction(entry_data):
    raw_entry(entry_data, 3, 80)
    confirm_legacy_body_mass_history(entry_data.engine, 3)
    entry_data.normalize_load_history()
    row = entry_data.load_sets_ui().iloc[0]
    sid, set_id = int(row.session_id), int(row.set_id)
    assert entry_data.load_original_set_load(set_id)["weight"] == 80
    entry_data.save_session_set_loads(sid, {set_id: SetLoad("bodyweight", 5, 80)})
    with pytest.raises(ValueError, match="edited after normalization"):
        entry_data.restore_original_set_load(sid, set_id)
    entry_data.save_session_set_loads(sid, {set_id: SetLoad("bodyweight", 0, 80)})
    assert entry_data.restore_original_set_load(sid, set_id)
    restored = entry_data.load_sets_ui().iloc[0]
    assert restored.weight == 80 and restored.load_type is None
    assert not entry_data.restore_original_set_load(sid, set_id)
    assert entry_data.normalize_load_history()["converted"] == 0


def test_saved_profiles_survive_renaming_and_future_history_cannot_change_a_past_default(
    entry_data,
):
    raw_entry(entry_data, 1, 0, day=date(2099, 1, 1), load=SetLoad("bodyweight", 0, 80))
    assert entry_data.load_exercise_load_profiles(on_date=DAY)[1].load_type == "external"
    profile = ExerciseLoadProfile(3, "bodyweight", "body_mass", "body_mass", "user")
    entry_data.save_exercise_load_profile(profile)
    with entry_data.engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE exercises SET exercise_name='Renamed movement' WHERE exercise_id=3"
        )
    assert entry_data.load_exercise_load_profiles(on_date=DAY)[3] == profile


@pytest.mark.parametrize("prefix", ["1. ", ""])
def test_explicit_added_weight_and_assistance_take_priority_over_a_remembered_txt_convention(
    entry_data, parser, prefix
):
    profile = ExerciseLoadProfile(3, "bodyweight", "body_mass", "body_mass", "user")
    entry_data.save_exercise_load_profile(profile)
    text = "1. Pull-up\n8x80 / 8x+5\nRIR 2/2"
    entries = entry_data.prepare_load_entries(parser._parse_txt(text), DAY)
    assert [s["load"] for s in entries[0]["sets"]] == [
        SetLoad("bodyweight", 0, 80),
        SetLoad("bodyweight", 5, 80),
    ]
    text = prefix + "Pull-up\nWeight: additional\nBody mass: 82\nAssistance: 20\n8x0\nRIR 2"
    entries = entry_data.prepare_load_entries(parser._parse_txt(text), DAY)
    assert entries[0]["sets"][0]["load"] == SetLoad("assisted_bodyweight", 0, 82, 20)


def test_total_weight_requires_body_mass_instead_of_inventing_additional_kg(entry_data):
    profile = ExerciseLoadProfile(3, "bodyweight", "total", "unknown", "user")
    entry_data.save_exercise_load_profile(profile)
    with pytest.raises(ValueError, match="body mass is needed"):
        entry_data.prepare_load_entries(
            [{"name": "Pull-up", "sets": [{"weight": 80, "reps": 8, "rir": 2}]}], date(2025, 1, 1)
        )


def test_normalized_external_history_opens_e1rm_for_the_entire_period(entry_data):
    raw_entry(entry_data, 1, 60)
    raw_entry(entry_data, 1, 65, day=date(2026, 2, 22), load=SetLoad("external", 65))
    entry_data.normalize_load_history()
    from mapper import map_exercise, map_workout_exercise, map_workout_session

    source = MetricsInput(
        [map_workout_session(row) for row in entry_data.load_sessions().to_dict("records")],
        [
            map_workout_exercise(row)
            for row in entry_data.load_workout_exercises().to_dict("records")
        ],
        [map_workout_set(row) for row in entry_data.load_sets_raw().to_dict("records")],
        [map_exercise(row) for row in entry_data.load_exercises().to_dict("records")],
        [],
        [],
        [],
        [],
    )
    metrics = compute_exercise_metrics(source)
    assert {point["load_type"] for point in metrics["per_exercise"][1]["per_set_performance"]} == {
        "external"
    }
    app = AppTest.from_string("""
import streamlit as st
from ui.exercise_progress_view import render_estimated_strength
render_estimated_strength(1, st.session_state['exercise'])
""")
    app.session_state["exercise"] = metrics["per_exercise"][1]
    app.run()
    assert not app.exception and not app.error and not app.info
    assert len(app.get("plotly_chart")) == 1
    assert app.metric[-1].value == "2"


def test_user_can_resolve_an_ambiguous_group_without_reentering_each_set(entry_data):
    raw_entry(entry_data, 4, 20)
    raw_entry(entry_data, 4, 25, day=date(2026, 2, 16))
    old = entry_data.load_exercise_load_profiles()[4]
    changed = replace(old, legacy_mode="assistance", source="user")
    report = entry_data.normalize_load_history(exercise_ids=(4,), overrides=(changed,))
    assert (report["converted"], report["unresolved"]) == (2, 0)
    rows = entry_data.load_sets_ui()
    assert set(rows.assistance_kg) == {20, 25}
    assert set(rows.weight) == {0}
