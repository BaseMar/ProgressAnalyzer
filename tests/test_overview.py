"""Current decisions, one recommendation home, disclosure and plan context."""

from dataclasses import replace
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from data_manager import DataManager
from mapper import map_workout_exercise, map_workout_session, map_workout_set
from metrics.input import MetricsInput
from metrics.overview_summary import overview_conclusion, workout_focus
from metrics.training_insights import compute_training_insights
from models.progression import (
    ExerciseRecommendation,
    SetGoal,
    TrainingBlockPhase,
    WorkoutRecommendation,
)
from models.training_insights import InsightReport
from test_next_workout_view import AS_OF, NEXT, START, seed
from test_plan_performance import data, execution
from test_plan_schedule import schedule_data as schedule_data

OVERVIEW_APP = """
import streamlit as st
from data_manager import DataManager
from ui.overview_view import OverviewView
manager = object.__new__(DataManager)
manager.engine = st.session_state['test_engine']
OverviewView(manager, {1: 'Bench Press', 2: 'Machine Chest Press'}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])
"""


def start_app(engine, saved, *, app_source=OVERVIEW_APP):
    app = AppTest.from_string(app_source, default_timeout=30)
    app.session_state["test_engine"] = engine
    app.session_state["adherence_plan"] = saved.plan_id
    app.session_state["as_of"] = AS_OF
    manager = DataManager(engine=engine)
    app.session_state["input_data"] = MetricsInput(
        sessions=[map_workout_session(row) for row in manager.load_sessions().to_dict("records")],
        workout_exercises=[
            map_workout_exercise(row) for row in manager.load_workout_exercises().to_dict("records")
        ],
        sets=[map_workout_set(row) for row in manager.load_sets_raw().to_dict("records")],
        exercises=[],
        exercise_muscle_targets=[],
        muscle_groups=[],
        body_measurements=[],
        body_composition=[],
        deload_exercise_ids=manager.load_deload_exercise_ids(as_of=AS_OF),
    )
    app.run()
    assert not app.exception
    assert not app.error
    return app


def markup(app):
    return "\n".join(item.value for item in app.markdown)


def target(action="maintain", *, pid=1, reason="mixed_loads"):
    return ExerciseRecommendation(
        pid,
        1,
        1,
        NEXT,
        action,
        () if action == "insufficient_data" else (SetGoal(60, 6, 10, "reps"),),
        2,
        reason,
        "Explain this target",
    )


def test_focus_highlights_changes_and_keeps_unchanged_targets_available():
    items = (
        target(pid=1),
        target("increase_weight", pid=2),
        target("increase_reps", pid=3),
        target("increase_reps", pid=4),
        target("insufficient_data", pid=5),
    )
    result = workout_focus(WorkoutRecommendation(TrainingBlockPhase("normal"), items))
    assert [item.plan_exercise_id for item in result.visible] == [2, 3]
    assert (result.available, result.total) == (4, 5)
    assert result.gaps[0].count == 1
    assert len(items) == 5


def test_repeated_missing_target_reasons_become_one_action():
    result = workout_focus(
        WorkoutRecommendation(
            TrainingBlockPhase("normal"),
            tuple(
                target("insufficient_data", pid=number, reason="missing_rir")
                for number in range(1, 8)
            ),
        )
    )
    assert result.visible == ()
    assert len(result.gaps) == 1
    assert result.gaps[0].count == 7
    assert result.gaps[0].example.reason_code == "missing_rir"


def test_focus_includes_maintained_loads_when_there_are_no_changes():
    result = workout_focus(WorkoutRecommendation(TrainingBlockPhase("normal"), (target(),)))
    assert result.visible[0].action == "maintain"
    assert result.available == 1


def test_overview_starts_with_progress_and_separates_next_workout(schedule_data):
    engine, _, _, _ = schedule_data
    saved = seed(schedule_data)
    app = start_app(engine, saved)
    html = markup(app)
    assert [item.label for item in app.tabs] == ["Progress", "Next workout"]
    assert [item.label for item in app.metric] == [
        "Improving exercises",
        "No clear change",
        "Lower results",
    ]
    assert [item.value for item in app.metric] == ["0", "1", "0"]
    assert any("Compared exercises: 1" in item.value for item in app.caption)
    assert "Your training today" not in html
    assert "62.5 kg · 3 × 6 reps" in html
    assert len(app.metric) == 3 and not app.dataframe and not app.get("plotly_chart")
    assert len([item for item in app.selectbox if item.label == "Active plan"]) == 1
    assert not any(
        item.label.startswith("Full workout") or item.label == "Why these targets?"
        for item in app.expander
    )
    # The annotation points to the target rather than copying its numbers.
    insight_html = [item.value for item in app.markdown if "analysis-insight" in item.value]
    assert all("62.5 kg" not in value for value in insight_html)


def test_default_focus_shows_recorded_starting_loads_when_source_rir_is_missing(schedule_data):
    engine, _, _, _ = schedule_data
    saved = seed(schedule_data, rir=None)
    app = start_app(engine, saved)
    assert any(item.value == "Your progress" for item in app.subheader)
    assert "62.5 kg" not in markup(app)
    assert "Source RIR is incomplete" in markup(app)
    assert all(item.value == "\u2014" for item in app.metric)
    assert any("Awaiting comparable data: 1" in item.value for item in app.caption)


def test_legacy_plan_shows_progression_without_requiring_a_block(schedule_data):
    engine, _, _, _ = schedule_data
    saved = seed(schedule_data, progression=False)
    app = start_app(engine, saved)
    assert any(item.value == "Your progress" for item in app.subheader)
    assert any("Normal training" in item.value for item in app.markdown)
    assert not any(item.label == "Workout details" for item in app.expander)
    assert "Target not available yet" not in markup(app)


def test_future_workout_selection_and_alternative_step_still_work_in_full_view(schedule_data):
    engine, _, _, _ = schedule_data
    saved = seed(schedule_data, actual_id=2)
    app = start_app(engine, saved)
    selector = next(item for item in app.selectbox if item.key.endswith("_exercise"))
    selector.select(2).run()
    next(item for item in app.number_input if "Weight step" in item.label).set_value(5.0).run()
    assert not app.exception
    assert "65 kg · 3 × 6 reps" in markup(app)
    assert "Instead of Bench Press" in markup(app)


def test_active_plan_survives_widget_cleanup_and_removed_plan_selection(schedule_data):
    engine, _, old, _ = schedule_data
    saved = seed(schedule_data)
    source = OVERVIEW_APP.replace(
        "OverviewView(manager, {1: 'Bench Press', 2: 'Machine Chest Press'}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])",
        "if not st.session_state.get('hide_overview'):\n    OverviewView(manager, {1: 'Bench Press', 2: 'Machine Chest Press'}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])",
    )
    app = start_app(engine, saved, app_source=source)
    assert app.session_state["active_plan_id"] == saved.plan_id
    app.session_state["hide_overview"] = True
    app.run()
    assert not app.selectbox
    app.session_state["hide_overview"] = False
    app.run()
    assert app.selectbox(key="adherence_plan").value == saved.plan_id
    app.session_state["hide_overview"] = True
    app.run()
    app.session_state["active_plan_id"] = 999999
    app.session_state["hide_overview"] = False
    app.run()
    assert not app.exception
    assert app.selectbox(key="adherence_plan").value in (old.plan_id, saved.plan_id)


def test_overview_contains_no_calendar_or_source_correction_widgets(schedule_data):
    engine, _, _, _ = schedule_data
    saved = seed(schedule_data)
    app = start_app(
        engine,
        saved,
        app_source="""
import pandas as pd
import streamlit as st
from data_manager import DataManager
from ui.overview_view import OverviewView
manager = object.__new__(DataManager)
manager.engine = st.session_state['test_engine']
OverviewView(manager, {1: 'Bench Press'}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])
""",
    )
    assert not any(item.label == "Calendar & recorded sessions" for item in app.expander)
    assert not any(item.key.startswith("history_date_") for item in app.button)
    assert len(app.metric) == 3 and not app.dataframe and not app.get("plotly_chart")


def test_recent_window_uses_actual_dates_including_early_and_moved_workouts():
    first = execution(1, date(2026, 4, 27))
    latest = execution(2, date(2026, 5, 25), (10, 10, 9))
    first = (
        replace(first[0], slot=replace(first[0].slot, performed_on=date(2026, 5, 11))),
        first[1],
        None,
    )
    latest = (
        replace(latest[0], slot=replace(latest[0].slot, performed_on=date(2026, 5, 18))),
        latest[1],
        None,
    )
    result = compute_training_insights(
        data(first, latest), as_of=AS_OF, start=date(2026, 5, 1), end=AS_OF, date_basis="performed"
    )
    assert result.annotations[0].code == "more_output"
    assert [item.session_id for item in result.annotations[0].sources] == [1, 2]
    with pytest.raises(ValueError, match="Date basis"):
        compute_training_insights(data(), as_of=AS_OF, date_basis="wrong")


def test_conclusion_uses_current_deload_phase_not_selected_future_workout(schedule_data):
    _, _, saved, _ = schedule_data
    from models.training_plan import ProgressionSettings

    version = replace(
        saved,
        draft=replace(saved.draft, effective_from=START, progression=ProgressionSettings(START, 7)),
    )
    conclusion = overview_conclusion(
        InsightReport((), 0, 0, 0), None, as_of=date(2026, 6, 15), version=version
    )
    assert conclusion.kind == "deload"
    assert "lighter week" in conclusion.title


def test_overview_has_clear_empty_and_unavailable_states(sample_input):
    for manager_source, expected in [
        (
            "SimpleNamespace(adherence_storage_ready=lambda: True, load_training_plans=lambda: [])",
            "Start with a Training Plan",
        ),
        ("SimpleNamespace(adherence_storage_ready=lambda: False)", "Plan analysis needs setup"),
    ]:
        app = AppTest.from_string(f"""
from types import SimpleNamespace
import streamlit as st
from ui.overview_view import OverviewView
OverviewView({manager_source}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])
""")
        app.session_state["input_data"] = replace(
            sample_input, sessions=[], workout_exercises=[], sets=[]
        )
        app.session_state["as_of"] = AS_OF
        app.run()
        assert not app.exception
        assert any(expected in item.value for item in app.info)
        assert any("No exercises recorded" in item.value for item in app.info)
        assert len(app.metric) == 3


def test_overview_displays_every_exercise_without_full_workout_disclosure(schedule_data):
    from db.training_plans import save_training_plan

    engine, _, _, _ = schedule_data
    saved = seed(schedule_data)
    day = saved.draft.days[0]
    exercises = tuple(replace(day.exercises[0], history_key=None) for _ in range(3))
    plan = save_training_plan(
        engine, replace(saved.draft, days=(replace(day, exercises=exercises),))
    )
    app = start_app(engine, plan)
    cards = next(item.value for item in app.markdown if 'class="recommendation-list"' in item.value)
    assert cards.count('class="recommendation-exercise"') == 3
    assert not any(
        item.label.startswith("Full workout") or item.label == "Why these targets?"
        for item in app.expander
    )


@pytest.mark.parametrize(
    "manager_source",
    [
        "SimpleNamespace(adherence_storage_ready=lambda: False)",
        "SimpleNamespace(adherence_storage_ready=lambda: True, load_training_plans=lambda: [])",
    ],
)
def test_recorded_progress_survives_absent_plan_or_plan_storage(manager_source):
    from test_recorded_progress import data as recorded_data
    from test_recorded_progress import entry

    app = AppTest.from_string(f"""
from types import SimpleNamespace
import streamlit as st
from ui.overview_view import OverviewView
OverviewView({manager_source}, {{1: 'Bench Press'}}, input_data=st.session_state['input_data']).render(as_of=st.session_state['as_of'])
""")
    app.session_state["as_of"] = AS_OF
    app.session_state["input_data"] = recorded_data(
        entry(1, date(2026, 4, 1), rir=1),
        entry(2, date(2026, 5, 18), (9, 9, 9), rir=1),
    )
    app.run()
    assert not app.exception and not app.error
    assert [item.value for item in app.metric] == ["1", "0", "0"]
    assert app.button(key="insight_history_more_output_1")


def test_changing_active_plan_does_not_change_recorded_progress(schedule_data):
    engine, _, original, _ = schedule_data
    saved = seed(schedule_data)
    app = start_app(engine, saved)
    before = [item.value for item in app.metric]
    app.selectbox(key="adherence_plan").select(original.plan_id).run()
    assert not app.exception and not app.error
    assert [item.value for item in app.metric] == before == ["0", "1", "0"]
