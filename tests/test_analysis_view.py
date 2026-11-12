"""Visible analysis navigation, stable choices and contextual source columns."""

from dataclasses import replace

from streamlit.testing.v1 import AppTest

from metrics.exercise_metrics import compute_exercise_metrics
from models.set_load import SetLoad
from test_load_analysis import source
from test_navigation_journeys import select_analysis_tab, start_app
from test_plan_schedule import schedule_data as schedule_data


def test_analysis_areas_are_visible_and_remembered_across_page_changes(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    assert [item.label for item in app.tabs] == [
        "Progress",
        "Exercises",
        "Plan consistency",
        "Muscles",
        "Body measurements",
    ]
    assert not app.button_group
    select_analysis_tab(app, "Body measurements")
    assert not any(item.key == "analysis_recorded_exercise" for item in app.selectbox)
    app.button(key="nav_Overview").click().run()
    app.button(key="nav_Analysis").click().run()
    assert not app.exception and not app.error
    assert app.session_state["analysis_tab"] == "Body measurements"
    assert app.selectbox(key="analysis_body_metric")


def test_progress_ranking_is_the_starting_tab_and_hidden_tabs_do_not_read_plans(sample_input):

    app = AppTest.from_string(
        """
import streamlit as st
import pandas as pd
from ui.analysis_view import AnalysisView
AnalysisView(st.session_state['input'], pd.DataFrame(), manager=object()).render()
""",
        default_timeout=30,
    )
    app.session_state["input"] = source(sample_input, [(60.0, 8), (65.0, 10)])
    app.run()
    assert not app.exception and not app.error
    assert app.session_state["analysis_tab"] == "Progress"
    assert any("Top 5 / Bottom 5" in item.value for item in app.subheader)
    assert not any(item.key == "analysis_recorded_exercise" for item in app.selectbox)
    assert len(app.get("plotly_chart")) == 1
    assert any("No decreases" in item.value for item in app.info)
    assert not app.dataframe
    assert not any(item.label in ("Filters", "Calculation details") for item in app.expander)
    select_analysis_tab(app, "Exercises")
    assert not app.exception
    assert app.selectbox(key="analysis_recorded_exercise")


def test_exercise_choice_survives_switching_analysis_areas_and_routes(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_recorded_exercise").select(2).run()
    select_analysis_tab(app, "Body measurements")
    select_analysis_tab(app, "Exercises")
    assert app.selectbox(key="analysis_recorded_exercise").value == 2
    app.button(key="nav_Overview").click().run()
    app.button(key="nav_Analysis").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="analysis_recorded_exercise").value == 2


def test_empty_period_keeps_the_selected_exercise_and_has_a_recovery_action(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_recorded_exercise").select(2).run()
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert app.selectbox(key="analysis_recorded_exercise").value == 2
    assert not app.get("plotly_chart") and not app.dataframe
    assert any("No recorded sets for this exercise" in item.value for item in app.info)
    app.button(key="analysis_show_all_history").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="analysis_recorded_exercise").value == 2
    assert app.selectbox(key="analysis_month").value == "All time"
    assert len(app.get("plotly_chart")) == 1


def test_duplicate_names_and_long_exercise_names_stay_selectable(
    schedule_data, sample_input, sets_dataframe
):
    name = "A very long exercise name with attachments and a detailed grip description " * 3
    input_data = replace(
        sample_input, exercises=[replace(item, name=name) for item in sample_input.exercises]
    )
    app = start_app(schedule_data, input_data, sets_dataframe, page="Analysis")
    choices = app.selectbox(key="analysis_recorded_exercise").options
    assert choices == [name + " - #1", name + " - #2"]
    app.selectbox(key="analysis_recorded_exercise").select(2).run()
    assert not app.exception and not app.error
    assert any(item.value.strip() == name.strip() for item in app.caption)


def test_no_workout_history_does_not_hide_other_analysis_areas(
    schedule_data, sample_input, sets_dataframe
):
    empty = replace(sample_input, sessions=[], workout_exercises=[], sets=[])
    app = start_app(schedule_data, empty, sets_dataframe.iloc[:0], page="Analysis")
    assert not any(item.key == "analysis_recorded_exercise" for item in app.selectbox)
    assert any("No exercise history yet" in item.value for item in app.info)
    select_analysis_tab(app, "Body measurements")
    assert not app.exception and not app.error
    assert len(app.get("vega_lite_chart")) == 1


def _exercise_app(input_data):
    app = AppTest.from_string("""
import streamlit as st
from ui.exercise_view import ExerciseView
ExerciseView(st.session_state['metrics']).render()
""")
    app.session_state["metrics"] = compute_exercise_metrics(input_data)
    app.run()
    assert not app.exception and not app.error
    return app


def test_exercise_chart_is_shown_without_a_recorded_sets_disclosure(sample_input):
    app = _exercise_app(source(sample_input, [(60.0, 8), (65.0, 9)]))
    assert len(app.get("plotly_chart")) == 1
    assert not app.dataframe
    assert not any(item.label == "Recorded sets" for item in app.expander)
    assert any("65 kg" in item.value and "9 reps" in item.value for item in app.caption)


def test_timed_chart_retains_missing_load_notice_without_a_source_table(sample_input):
    app = _exercise_app(
        source(
            sample_input,
            [
                (SetLoad("assisted_bodyweight", 0, 80, 20), 40),
                (SetLoad("assisted_bodyweight", 0, None, 20), 50),
            ],
            timed=True,
        )
    )
    assert len(app.get("plotly_chart")) == 1
    assert not app.dataframe
    assert not any(item.label == "Recorded sets" for item in app.expander)
    assert any("Some load values are missing" in item.value for item in app.caption)


def test_ranking_measure_switch_keeps_seconds_and_strength_estimates_separate(sample_input):
    strength = source(sample_input, [(60.0, 8), (65.0, 10)])
    timed = source(sample_input, [(0.0, 30), (0.0, 40)], timed=True)
    mixed = replace(
        strength,
        workout_exercises=strength.workout_exercises
        + [
            replace(item, workout_exercise_id=item.workout_exercise_id + 1000)
            for item in timed.workout_exercises
        ],
        sets=strength.sets
        + [
            replace(item, workout_exercise_id=item.workout_exercise_id + 1000)
            for item in timed.sets
        ],
    )
    app = AppTest.from_string(
        """
import streamlit as st
import pandas as pd
from ui.analysis_view import AnalysisView
AnalysisView(st.session_state['input'],pd.DataFrame(),manager=object()).render()
""",
        default_timeout=30,
    )
    app.session_state["input"] = mixed
    app.run()
    assert not app.exception
    assert app.selectbox(key="analysis_ranking_measure").value == "Estimated strength"
    app.selectbox(key="analysis_ranking_measure").select("Hold time").run()
    assert not app.exception
    assert any(item.value.startswith("Hold time ·") for item in app.caption)
    import json

    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert chart["data"][0]["customdata"][0][1:3] == [30, 40]
    assert not app.dataframe


def test_one_visible_period_is_shared_across_all_analysis_tabs(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_month").select("2026-05").run()
    for tab in ("Progress", "Exercises", "Plan consistency", "Muscles", "Body measurements"):
        select_analysis_tab(app, tab)
        assert not app.exception and not app.error
        assert len([item for item in app.selectbox if item.key == "analysis_month"]) == 1
        assert app.selectbox(key="analysis_month").value == "2026-05"
        assert not any(item.label == "Filters" for item in app.expander)
    assert not app.dataframe
