"""Actual page switches, draft persistence and one home for each task."""

from streamlit.testing.v1 import AppTest

from db.training_plans import load_training_plans
from test_plan_schedule import schedule_data as schedule_data
from ui.utils.data_filter import filter_data_by_month

APP = """
import pandas as pd
import streamlit as st
from data_manager import DataManager
from metrics.measurement_timeline import measurement_timeline
from ui.sidebar_view import SidebarView
from ui.overview_view import OverviewView
from ui.analysis_view import AnalysisView
from ui.history_view import HistoryView
from ui.training_plan_view import TrainingPlanView
manager = object.__new__(DataManager)
manager.engine = st.session_state['test_engine']
input_data = st.session_state['input_data']
frame = st.session_state['sets_df']
page = SidebarView().render_navigation()
names = {exercise.exercise_id: exercise.name for exercise in input_data.exercises}
if page == 'Overview':
    OverviewView(manager, names).render()
elif page == 'Analysis':
    AnalysisView(input_data, frame, manager=manager, exercise_names=names).render()
elif page == 'Plan':
    TrainingPlanView(input_data.exercises, manager).render()
else:
    HistoryView({'body': {'timeline': measurement_timeline(input_data)}}, frame, data_manager=manager, exercise_names=names).render()
"""


def start_app(schedule_data, sample_input, sets_dataframe, page="Overview"):
    app = AppTest.from_string(APP, default_timeout=45)
    app.session_state["test_engine"] = schedule_data[0]
    app.session_state["input_data"] = sample_input
    frame = sets_dataframe.assign(repetitions=8, weight=60.0, set_number=1)
    app.session_state["sets_df"] = frame
    app.session_state["nav_selected"] = page
    app.run()
    assert not app.exception
    assert not app.error
    return app


def test_four_pages_and_add_workout_shortcut_open_only_history_import(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe)
    assert {item.label for item in app.sidebar.button} == {
        "Overview",
        "Analysis",
        "Plan",
        "History",
        "Import workout TXT",
    }
    assert not app.get("file_uploader")
    assert not any(item.key.startswith("history_date_") for item in app.button)
    assert not app.sidebar.selectbox
    app.button(key="nav_add_workout").click().run()
    assert not app.exception
    assert app.session_state["nav_selected"] == "History"
    assert len(app.get("file_uploader")) == 1
    assert not app.sidebar.get("file_uploader")
    assert any(item.key.startswith("history_date_") for item in app.button)
    app.button(key="history_close_import").click().run()
    assert not app.get("file_uploader")
    app.button(key="nav_Analysis").click().run()
    assert not app.get("file_uploader")
    assert not any(item.key.startswith("history_date_") for item in app.button)
    assert not any(item.label == "Upcoming workout" for item in app.selectbox)


def test_one_exercise_form_and_draft_survive_navigation_before_saving(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Plan")
    app.button(key="plan_create_new").click().run()
    app.text_input(key="plan_editor_new_name").set_value("Persistent draft")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Upper A")
    app.selectbox(key="plan_editor_new_day_0_ex_0_exercise_id").select(1)
    app.button(key="plan_editor_new_day_0_add_exercise").click().run()
    assert len([item for item in app.selectbox if item.label == "Exercise"]) == 1
    app.selectbox(key="plan_editor_new_day_0_ex_1_exercise_id").select(1)
    app.number_input(key="plan_editor_new_day_0_ex_1_sets").set_value(5)
    app.number_input(key="plan_editor_new_day_0_ex_1_rir").set_value(1)
    app.button(key="nav_Overview").click().run()
    assert not app.exception
    assert not app.text_input
    app.button(key="nav_Plan").click().run()
    assert not app.exception
    assert app.session_state["plan_create_mode"] is True
    assert app.text_input(key="plan_editor_new_name").value == "Persistent draft"
    assert app.selectbox(key="plan_editor_new_day_0_active_exercise").value == 1
    assert app.number_input(key="plan_editor_new_day_0_ex_1_sets").value == 5
    assert app.number_input(key="plan_editor_new_day_0_ex_1_rir").value == 1
    app.selectbox(key="plan_editor_new_day_0_active_exercise").select(0).run()
    assert app.number_input(key="plan_editor_new_day_0_ex_0_sets").value == 3
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception
    assert not app.error
    saved = next(
        item
        for item in load_training_plans(schedule_data[0])
        if item.draft.name == "Persistent draft"
    )
    assert [item.set_count for item in saved.draft.days[0].exercises] == [3, 5]
    assert saved.draft.days[0].exercises[1].target_rir == 1
    assert app.session_state["active_plan_id"] == saved.plan_id


def test_analysis_period_applies_to_body_data_and_keeps_other_questions_hidden(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_question").select("Body measurements").run()
    app.selectbox(key="analysis_month").select("2026-05").run()
    app.selectbox(key="analysis_body_metric").select("Waist").run()
    assert not app.exception
    assert len(app.get("vega_lite_chart")) == 1
    assert len(app.metric) == 3 and not app.form
    assert not any(
        item.label in ("Explore an exercise", "Upcoming workout") for item in app.selectbox
    )
    assert [item.value for item in app.metric] == ["80 cm", "—", "01 May 2026"]
    assert any("One observation" in item.value for item in app.caption)
    records = app.dataframe[0].value
    assert len(records) == 1
    assert records["Waist"].iloc[0] == 80
    app.button(key="nav_Overview").click().run()
    assert not any(item.label == "Analysis period" for item in app.selectbox)
    assert any(item.label == "Upcoming workout" for item in app.selectbox)
    app.button(key="nav_Analysis").click().run()
    assert app.selectbox(key="analysis_month").value == "2026-05"


def test_plan_consistency_has_one_chart_and_no_editing_or_exercise_drilldown(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_question").select("Plan consistency").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert len(app.metric) == 3 and not app.text_input
    assert not any(
        item.label in ("Explore an exercise", "Linked workout", "Upcoming workout")
        for item in app.selectbox
    )
    assert app.metric[0].label == "Workouts with linked logs"


def test_recorded_exercise_analysis_preserves_unplanned_exercises_without_rankings(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    assert not any(item.key == "analysis_exercise_scope" for item in app.radio)
    assert app.selectbox(key="analysis_month").value == "All time"
    assert next(item for item in app.expander if item.label == "Filters").proto.expanded is False
    assert not app.exception
    app.selectbox(key="analysis_recorded_exercise").select(2).run()
    assert len(app.get("plotly_chart")) == 1
    assert not app.metric
    assert any("60 kg" in item.value and "12 reps" in item.value for item in app.caption)
    assert any("1 logged sets across 1 sessions" in item.value for item in app.caption)
    assert not any(
        "Top Strength" in item.value or "Weakest Strength" in item.value for item in app.markdown
    )
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert not app.exception
    assert app.selectbox(key="analysis_recorded_exercise").value == 1


def test_history_body_input_and_overlay_are_reachable_without_other_page_forms(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="History")
    assert not app.form
    app.button(key="history_add_measurement_button").click().run()
    assert not app.exception
    assert len(app.form) == 2
    assert not app.get("file_uploader")
    assert not any(item.label == "Upcoming workout" for item in app.selectbox)
    app.toggle(key="calendar_plan_overlay").set_value(False).run()
    assert not app.exception
    assert app.session_state["active_plan_id"] == schedule_data[2].plan_id


def test_shared_month_filter_filters_measurements_even_when_no_workout_rows(
    sample_input, sets_dataframe
):
    filtered, frame = filter_data_by_month(sample_input, sets_dataframe.iloc[:0], "2026-05")
    assert frame.empty
    assert all(item.date.month == 5 for item in filtered.body_measurements)
    assert all(item.date.month == 5 for item in filtered.body_composition)


def test_first_body_measurement_is_visible_without_composition_records(sample_input):
    from dataclasses import replace

    from metrics.measurement_timeline import measurement_timeline

    only_measurement = replace(
        sample_input, body_composition=[], body_measurements=sample_input.body_measurements[:1]
    )
    assert measurement_timeline(only_measurement) == [
        {"date": sample_input.body_measurements[0].date, "waist": 82.0}
    ]


def test_analysis_accepts_mixed_database_date_representations(
    schedule_data, sample_input, sets_dataframe
):
    from dataclasses import replace

    import pandas as pd

    mixed = replace(
        sample_input,
        body_measurements=[
            replace(item, date=str(item.date)) for item in sample_input.body_measurements
        ],
        body_composition=[
            replace(item, date=pd.Timestamp(item.date)) for item in sample_input.body_composition
        ],
    )
    app = start_app(schedule_data, mixed, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_question").select("Body measurements").run()
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert not app.exception
    assert len(app.get("vega_lite_chart")) == 1


def test_history_main_actions_open_import_and_manual_entry_directly(
    schedule_data, sample_input, sets_dataframe, monkeypatch
):
    import pandas as pd

    from data_manager import DataManager

    monkeypatch.setattr(
        DataManager,
        "load_exercises",
        lambda self: pd.DataFrame([{"exercise_id": 1, "exercise_name": "Bench Press"}]),
    )
    app = start_app(schedule_data, sample_input, sets_dataframe, page="History")
    assert app.button(key="history_add_workout_button").label == "Import workout TXT"
    app.button(key="history_add_workout_button").click().run()
    assert not app.exception
    assert len(app.get("file_uploader")) == 1
    assert not any(item.key == "workout_entry_mode" for item in app.radio)
    app.button(key="history_manual_workout_button").click().run()
    assert not app.exception
    assert app.session_state["workout_entry_mode"] == "Enter exercise"
    assert not app.get("file_uploader")
    assert app.button(key="entry_save")
    assert not app.error


def test_create_plan_button_and_back_preserve_draft(schedule_data, sample_input, sets_dataframe):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Plan")
    app.button(key="plan_create_new").click().run()
    app.text_input(key="plan_editor_new_name").set_value("My draft").run()
    assert not app.checkbox(key="plan_editor_new_progression_enabled").value
    app.button(key="plan_back_to_saved").click().run()
    assert not app.exception and not app.text_input
    app.button(key="plan_create_new").click().run()
    assert not app.exception
    assert app.text_input(key="plan_editor_new_name").value == "My draft"


def test_highlight_opens_exact_exercise_and_clears_hidden_date_filter(
    schedule_data, sample_input, sets_dataframe
):
    from dataclasses import replace

    from metrics.training_insights import compute_training_insights
    from test_plan_performance import data, execution
    from test_training_insights import AS_OF, FIRST, PLAN, SECOND

    planned = replace(PLAN, exercise_id=2)
    report = compute_training_insights(
        data(
            execution(1, FIRST, actual_id=2, planned=planned),
            execution(2, SECOND, (10, 10, 9), actual_id=2, planned=planned),
        ),
        as_of=AS_OF,
    )
    source = APP.replace(
        "    OverviewView(manager, names).render()",
        "    from ui.training_insights_view import render_training_insights\n    render_training_insights(st.session_state['test_report'], names)",
    )
    app = AppTest.from_string(source, default_timeout=45)
    app.session_state["test_engine"] = schedule_data[0]
    app.session_state["input_data"] = sample_input
    app.session_state["sets_df"] = sets_dataframe
    app.session_state["test_report"] = report
    app.session_state["analysis_period_value"] = "2026-05"
    app.run()
    assert not app.exception
    app.button(key="insight_history_more_output_2").click().run()
    assert not app.exception and not app.error
    assert app.session_state["nav_selected"] == "Analysis"
    assert app.selectbox(key="analysis_recorded_exercise").value == 2
    assert app.selectbox(key="analysis_month").value == "All time"
