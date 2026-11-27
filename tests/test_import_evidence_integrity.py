from datetime import date, time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import event, text
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from db.bootstrap import bootstrap_database
from db.plan_adherence import actual_exercises
from db.plan_schedule import sessions
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft
from test_bootstrap import fresh_engine as fresh_engine
from ui.sidebar_upload import SidebarUpload

START = date(2026, 5, 4)
PRESS = PlannedExercise(1, 3, 8, 12, target_rir=2, weight_increment=2.5)


class ImportState(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


@pytest.fixture
def manager(fresh_engine):
    if fresh_engine.dialect.name == "sqlite":

        @event.listens_for(fresh_engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    bootstrap_database(fresh_engine)
    with fresh_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO exercises (exercise_name) VALUES "
                "('Audit Press'), ('Audit Press!'), ('Audit Row'), "
                "('Audit-Bridge'), ('Audit–Bridge'), ('Audit Press-')"
            )
        )
    return DataManager(engine=fresh_engine)


@pytest.fixture
def upload_ui(monkeypatch):
    events = SimpleNamespace(
        warnings=[], errors=[], reruns=[], state=ImportState(exercise_mapping={})
    )
    sink = SimpleNamespace(
        warning=events.warnings.append, error=events.errors.append, success=lambda _: None
    )
    monkeypatch.setattr(
        "ui.sidebar_upload.st",
        SimpleNamespace(
            sidebar=sink, session_state=events.state, rerun=lambda: events.reruns.append(True)
        ),
    )
    return events


@pytest.mark.parametrize(
    ("name", "expected_id"),
    [
        ("Audit Press", 1),
        ("Audit Press!", 2),
        ("aUDIT rOw", 3),
        ("Audit Row?", 3),
        ("Audit–Bridge", 5),
        ("Audit Press-", 6),
    ],
)
def test_import_resolves_review_and_persistence_to_one_catalog_id(
    manager, upload_ui, name, expected_id
):
    upload = SidebarUpload(manager=manager, sidebar=True)
    parsed = upload._parse_txt(f"1. {name}\n8x60\nRIR: 2")
    reviewed = upload._review_loads(parsed, START, "test")
    upload._process(reviewed, START, time(8), time(9))
    assert manager.load_workout_exercises().exercise_id.tolist() == [expected_id]
    assert reviewed[0]["exercise_id"] == expected_id
    assert not upload_ui.errors


@pytest.mark.parametrize("name", ["AUDIT PRESS", "Audit Press?", "Unknown lift"])
def test_import_requires_a_choice_for_ambiguous_and_unknown_names(manager, upload_ui, name):
    upload = SidebarUpload(manager=manager, sidebar=True)
    parsed = upload._parse_txt(f"1. {name}\n8x60\nRIR: 2")
    upload._process(upload._review_loads(parsed, START, "test"), START, time(8), time(9))
    assert manager.load_workout_exercises().empty
    assert upload_ui.state.pending_exercise == name
    assert upload_ui.reruns == [True]
    upload_ui.state.exercise_mapping[name] = 2
    reviewed = upload._review_loads(parsed, START, "test")
    upload._process(reviewed, START, time(8), time(9))
    assert reviewed[0]["exercise_id"] == 2
    assert manager.load_workout_exercises().exercise_id.tolist() == [2]


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ("Result: working: 11x60 / 10x60 / 9x60", [False, False, False]),
        ("Result: warm-up: 12x20 / 10x35 / working: 10x60 / 8x60", [True, True, False, False]),
        ("Result: warm–up: 12x20 / 10x35 / working: 10x60 / 8x60", [True, True, False, False]),
        ("Wynik: rozgrzewka: 20s / 25s / robocze: 40s @5 / 1:00", [True, True, False, False]),
    ],
)
def test_result_purpose_applies_to_the_entire_group(upload_ui, result, expected):
    upload = object.__new__(SidebarUpload)
    parsed = upload._parse_txt(f"1. Audit Press\n{result}\nResult: 7x70\n2. Audit Row\n8x45")
    assert [item.get("is_warmup") for item in parsed[0]["sets"]] == [*expected, None]
    assert "is_warmup" not in parsed[1]["sets"][0]
    if result.startswith("Wynik"):
        assert [(item.get("duration_seconds"), item["weight"]) for item in parsed[0]["sets"]] == [
            (20, 0),
            (25, 0),
            (40, 5),
            (60, 0),
            (None, 70),
        ]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("\nResult: 11x60 / 10x60 / 9x60\nRIR: 2 / / 1", [2, None, 1]),
        (": 11x60 / 10x60 / 9x60 RIR / 0 /", [None, 0, None]),
        (": 11x60 RIR 2 / 10x60 / 9x60 RIR 0", [2, None, 0]),
        (": 11x60 / 10x60 RIR 0 / 9x60", [None, 0, None]),
        (": 11×60 RIR 2, 10✕60 RIR ?, 9x60 RIR 0", [2, None, 0]),
        (": 11x60 / 10x60 / 9x60 RIR 1:05", [None, None, None]),
        ("\n11x60 / 10x60 / 9x60\nRIR: ? / _ / 0", [None, None, 0]),
        ("\n11x60 / 10x60 / 9x60\nRIR: 0", [0, None, None]),
        ("\n11x60 / 10x60 / 9x60\nRIR: 2 / bad / 1 / 3", [2, None, 1]),
        ("\n11x60 / 10x60 / 9x60\nRIR: 2 / -1 / 0", [2, None, 0]),
    ],
)
def test_positional_rir_in_inline_and_multiline_syntax(upload_ui, body, expected):
    upload = object.__new__(SidebarUpload)
    exercises = upload._parse_txt("1. Audit Press" + body)
    assert [item["rir"] for item in exercises[0]["sets"]] == expected
    if "bad" in body:
        assert any("invalid" in warning.lower() for warning in upload_ui.warnings)
        assert any("excess" in warning.lower() for warning in upload_ui.warnings)
    if "-1" in body or "1:05" in body:
        assert any("invalid" in warning.lower() for warning in upload_ui.warnings)


def workout_plan(manager, *days):
    return manager.save_training_plan(TrainingPlanDraft("Fixture", START, days))


def saved_slot(manager, plan, day):
    return manager.load_scheduled_workouts(plan.plan_id, day, day)[0]


def recommendation(manager, plan, day, **options):
    slot = saved_slot(manager, plan, day)
    return manager.load_workout_recommendations(
        plan.plan_id, slot.day_id, day, as_of=day, **options
    ).exercises[0]


def record(
    manager, day, catalog_id, reps=(12, 12, 12), *, start=time(8), plan=None, scheduled=None
):
    manager.add_workout_session(
        day,
        "Synthetic",
        [
            {
                "name": "Fixture",
                "exercise_id": catalog_id,
                "sets": [{"reps": value, "weight": 60, "rir": 2} for value in reps],
            }
        ],
        start,
    )
    session_id = int(manager.load_sessions().session_id.max())
    if plan is not None:
        slot = saved_slot(manager, plan, scheduled or day)
        manager.assign_scheduled_session(slot.day_id, slot.scheduled_date, session_id)
    return session_id


def test_imported_purpose_and_rir_agree_with_review_and_recommendation(manager, upload_ui):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    upload = SidebarUpload(manager=manager, sidebar=True)
    parsed = upload._parse_txt(
        "1. Audit Press\n"
        "Result: warm-up: 12x20 / 10x35 / working: 11x60 / 10x60 / 9x60\n"
        "RIR: 2 / 1 / 6 / / 6"
    )
    reviewed = upload._review_loads(parsed, START, "test")
    upload._process(reviewed, START, time(8), time(9))
    session_id = int(manager.load_sessions().iloc[0].session_id)
    persisted = manager.load_session_sets(session_id).astype(object)
    expected = [
        (12, 20, 2, True),
        (10, 35, 1, True),
        (11, 60, 6, False),
        (10, 60, None, False),
        (9, 60, 6, False),
    ]
    assert [
        (s["reps"], s["weight"], s["rir"], s.get("is_warmup")) for s in reviewed[0]["sets"]
    ] == expected
    assert (
        list(
            persisted.where(persisted.notna(), None)[
                ["repetitions", "weight", "rir", "is_warmup"]
            ].itertuples(index=False, name=None)
        )
        == expected
    )
    item = recommendation(manager, plan, START + timedelta(days=7))
    assert item.reason_code == "missing_rir"
    assert item.evidence_session_ids == (session_id,)
    assert [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals] == [
        (60, 11, 11),
        (60, 10, 10),
        (60, 9, 9),
    ]


def test_streamlit_requires_explicit_catalog_selection_and_shows_saved_set_data(manager):
    app = AppTest.from_string("""
import streamlit as st
from ui.sidebar_upload import SidebarUpload
SidebarUpload(manager=st.session_state['audit_manager'], sidebar=True).render()
""")
    app.session_state["audit_manager"] = manager
    upload = SimpleNamespace(
        name="synthetic.txt",
        getvalue=lambda: b"1. AUDIT PRESS\nResult: Working: 11x60 / 10x60 / 9x60\nRIR: 2 / / 0",
    )
    with patch("streamlit.sidebar.file_uploader", return_value=upload):
        app.run()
        next(button for button in app.button if button.label == "Import workout").click().run()
        assert not app.exception
        assert any("multiple catalog entries" in item.value for item in app.warning)
        choice = app.selectbox[0]
        assert choice.value is None
        assert choice.options == ["Audit Press", "Audit Press!", "Audit Press-"]
        assert manager.load_workout_exercises().empty
        choice.set_value(1).run()
        next(
            button for button in app.button if button.label == "Use selected exercise"
        ).click().run()

        preview = app.get("table")[0].value
        assert preview["Exercise"].tolist() == ["Audit Press"] * 3
        assert preview["RIR"].tolist() == ["2", "—", "0"]
        assert preview["Purpose"].tolist() == ["Working"] * 3
        next(button for button in app.button if button.label == "Import workout").click().run()
        assert not app.exception and not app.error
        assert manager.load_workout_exercises().exercise_id.tolist() == [1]
        saved = manager.load_session_sets(int(manager.load_sessions().iloc[0].session_id)).astype(
            object
        )
        assert saved.where(saved.notna(), None)["rir"].tolist() == [2, None, 0]
        assert saved["is_warmup"].tolist() == [False] * 3


def test_service_retains_linked_omission_and_allows_later_valid_execution(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    older = record(manager, START, 1, plan=plan)
    omitted_date = START + timedelta(days=8)
    omission = record(manager, omitted_date, 3, plan=plan, scheduled=START + timedelta(days=7))
    item = recommendation(manager, plan, START + timedelta(days=14))
    assert (item.action, item.reason_code, item.goals) == (
        "insufficient_data",
        "incomplete_sets",
        (),
    )
    assert item.evidence_session_ids == (omission,)
    assert item.evidence_dates == (omitted_date,)
    assert item.evidence_workouts == ("Press",)
    assert older != omission
    assert manager.load_workout_exercises().exercise_id.tolist() == [1, 3]
    complete = record(manager, START + timedelta(days=14), 1, plan=plan)
    item = recommendation(manager, plan, START + timedelta(days=21))
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (complete,)


def test_service_keeps_partial_unlinked_and_cross_plan_performance(manager):
    plan = workout_plan(
        manager,
        TrainingDay("Press", 0, (PRESS,)),
        TrainingDay("Row", 1, (PlannedExercise(3, 3, 8, 12),)),
    )
    another = workout_plan(manager, TrainingDay("Another press", 0, (PRESS,)))
    older = record(manager, START, 1, plan=another)
    record(manager, START + timedelta(days=1), 3, plan=plan)
    day = START + timedelta(days=7)
    item = recommendation(manager, plan, day)
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (older,)
    partial = record(manager, day, 1, (11, 10), plan=plan)
    item = recommendation(manager, plan, day + timedelta(days=7))
    assert item.reason_code == "incomplete_sets" and item.evidence_session_ids == (partial,)
    assert [(goal.weight, goal.minimum, goal.maximum) for goal in item.goals] == [
        (60, 11, 11),
        (60, 10, 10),
        (None, 8, 12),
    ]
    unlinked = record(manager, day + timedelta(days=6), 1)
    item = recommendation(manager, plan, day + timedelta(days=7))
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (unlinked,)


def test_service_preserves_replacements_and_same_day_actual_order(manager):
    plan = workout_plan(manager, TrainingDay("Press", 0, (PRESS,)))
    older = record(manager, START, 1, plan=plan)
    day = START + timedelta(days=7)
    replacement = record(manager, day, 3, plan=plan)
    slot = saved_slot(manager, plan, day)
    prepared = manager.prepare_plan_context(plan.plan_id, day, day, as_of=day)
    target = prepared.prepare_workout(slot.day_id, day).upcoming.targets[0].plan_exercise_id
    replacement_entry = int(manager.load_workout_exercises().workout_exercise_id.max())
    manager.save_exercise_match(replacement, target, replacement_entry)
    upcoming = day + timedelta(days=7)
    item = recommendation(manager, plan, upcoming)
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (older,)
    item = recommendation(
        manager, plan, upcoming, substitutions={target: 3}, replacement_weight_steps={3: 5}
    )
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (
        replacement,
    )
    assert item.actual_exercise_id == 3 and item.goals[0].weight == 65

    manager.remove_exercise_match(replacement, target)
    # This unlinked entry has a higher ID, but was performed earlier than the omission.
    with manager.engine.begin() as connection:
        earlier = connection.execute(
            sessions.insert()
            .values(session_date=day, start_time=time(7))
            .returning(sessions.c.session_id)
        ).scalar_one()
        connection.execute(
            actual_exercises.update()
            .where(actual_exercises.c.session_id == older)
            .values(session_id=earlier)
        )
    item = recommendation(manager, plan, upcoming)
    assert item.reason_code == "incomplete_sets" and item.evidence_session_ids == (replacement,)
    with manager.engine.begin() as connection:
        connection.execute(
            sessions.update().where(sessions.c.session_id == earlier).values(start_time=time(9))
        )
    item = recommendation(manager, plan, upcoming)
    assert item.reason_code == "upper_range_confirmed" and item.evidence_session_ids == (earlier,)
