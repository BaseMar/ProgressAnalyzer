"""Exercise sections retain latest evidence, units and existing strength estimates."""

import json
from dataclasses import replace
from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.progress_ranking import rank_exercise_progress
from metrics.recorded_progress import compare_recorded_exercise, compute_recorded_progress
from models.set_load import SetLoad
from test_navigation_journeys import select_analysis_tab, start_app
from test_plan_schedule import schedule_data as schedule_data
from test_recorded_progress import AS_OF, FIRST, SECOND, data, entry
from ui.utils.data_filter import filter_data_by_month


def exercise_app(input_data, section, *, month="All time"):
    import pandas as pd

    filtered, _ = filter_data_by_month(input_data, pd.DataFrame(), month)
    app = AppTest.from_string("""
import streamlit as st
from ui.exercise_view import ExerciseView
from ui.exercise_progress_view import render_estimated_strength, render_latest_comparison
if st.session_state['section'] == 'Latest comparison':
    render_latest_comparison(st.session_state['input'], 1, st.session_state['month'])
elif st.session_state['section'] == 'Estimated strength':
    render_estimated_strength(1, st.session_state['metrics']['per_exercise'].get(1, {}))
else:
    ExerciseView(
        st.session_state['metrics'], input_data=st.session_state['input'],
        selected_month=st.session_state['month'], exercise_options={1: 'Bench Press'},
    ).render()
""")
    app.session_state["metrics"] = compute_exercise_metrics(filtered)
    app.session_state["input"] = input_data
    app.session_state["month"] = month
    app.session_state["section"] = section
    app.run()
    assert not app.exception and not app.error
    return app


@pytest.mark.parametrize(
    "options,code",
    [({}, "more_output"), ({"weight": 65}, "load_changed"), ({"rir": 0}, "effort_changed")],
)
def test_exercise_detail_reuses_overview_verdict_and_evidence(options, code):
    recorded = data(entry(1, FIRST), entry(2, SECOND, (9, 8, 8), **options))
    detail = compare_recorded_exercise(recorded, 1, as_of=AS_OF, start=date(2026, 11, 1))
    overview = compute_recorded_progress(recorded, as_of=AS_OF).annotations[0]
    assert detail == overview and detail.code == code
    assert [source.session_id for source in detail.sources] == [1, 2]


@pytest.mark.parametrize(
    "options,reason",
    [
        ({"rir": None}, "Missing RIR"),
        ({"values": ()}, "No recorded working sets"),
        ({"values": (8, 8)}, "Working set count changed"),
    ],
)
def test_latest_incomplete_execution_is_kept_in_comparison(options, reason):
    recorded = data(
        entry(1, FIRST),
        entry(2, date(2026, 10, 12), (9, 8, 8)),
        entry(3, SECOND, **options),
    )
    detail = compare_recorded_exercise(recorded, 1, as_of=AS_OF)
    assert detail.code == "limited_evidence" and reason in detail.evidence
    assert [source.session_id for source in detail.sources] == [2, 3]


def test_exercise_pair_is_not_limited_by_overview_annotation_count():
    recorded = data(
        *(
            entry(sid, day, (sid + 7,) * 3, eid=eid)
            for eid in range(1, 9)
            for sid, day in ((1, FIRST), (2, SECOND))
        )
    )
    assert len(compute_recorded_progress(recorded, as_of=AS_OF).annotations) == 5
    assert compare_recorded_exercise(recorded, 8, as_of=AS_OF).exercise_id == 8
    assert compare_recorded_exercise(recorded, 9, as_of=AS_OF) is None
    assert compare_recorded_exercise(recorded, 1, as_of=AS_OF, start=AS_OF) is None


def test_period_cutoff_does_not_use_newer_or_future_sessions():
    recorded = data(
        entry(1, FIRST),
        entry(2, SECOND, (9, 8, 8)),
        entry(3, date(2026, 11, 20), (1, 1, 1)),
    )
    assert compare_recorded_exercise(recorded, 1, as_of=AS_OF).sources[-1].session_id == 2
    detail = compare_recorded_exercise(recorded, 1, as_of=AS_OF, end=FIRST)
    assert detail.code == "limited_evidence" and len(detail.sources) == 1


def test_comparison_panel_shows_per_set_results_and_previous_month_evidence():
    app = exercise_app(
        data(entry(1, FIRST), entry(2, SECOND, (9, 8, 8))), "Latest comparison", month="2026-11"
    )
    assert [item.value for item in app.metric] == ["+1"]
    assert not app.get("plotly_chart")
    table = app.dataframe[0].value
    assert list(table.columns) == ["Working set", "Previous · 05 Oct 2026", "Latest · 10 Nov 2026"]
    assert table.iloc[0, 1] == "60 kg × 8 reps · RIR 1"
    assert table.iloc[0, 2] == "60 kg × 9 reps · RIR 1"
    assert not app.caption
    page = exercise_app(data(entry(1, FIRST), entry(2, SECOND, (9, 8, 8))), "All", month="2026-11")
    assert [item.value for item in page.subheader] == [
        "Recorded history",
        "Estimated strength",
        "Latest comparison",
    ]
    assert len(page.get("plotly_chart")) == 2 and len(page.dataframe) == 1
    assert [item.label for item in page.selectbox] == ["Exercise"]


def test_comparison_missing_set_and_rir_are_not_shown_as_zero_or_progress():
    app = exercise_app(
        data(entry(1, FIRST), entry(2, SECOND, (9, 8), rir=None)), "Latest comparison"
    )
    assert not app.metric
    assert any("Missing RIR" in item.value for item in app.info)
    table = app.dataframe[0].value
    assert table.iloc[0, 2].endswith("RIR ?")
    assert table.iloc[2, 2] == "—"


def test_empty_latest_execution_is_visible_even_without_metric_points():
    app = exercise_app(
        data(entry(1, FIRST), entry(2, SECOND, ())), "Latest comparison", month="2026-11"
    )
    assert any("No recorded working sets" in item.value for item in app.info)
    assert len(app.dataframe[0].value) == 3
    assert not app.metric


def test_changed_convention_is_explained_and_cannot_be_filtered_to_an_older_pair():
    recorded = data(entry(1, FIRST), entry(2, SECOND, weight=60, load=SetLoad("external", 60)))
    app = exercise_app(recorded, "All")
    assert any("Load convention changed" in item.value for item in app.info)
    assert not app.metric
    app.selectbox(key="recorded_load_convention").select("legacy").run()
    assert not app.exception
    assert any("Load convention changed" in item.value for item in app.info)
    assert "Latest · 10 Nov 2026" in app.dataframe[0].value.columns


def test_timed_deload_and_mixed_units_keep_seconds_in_the_source_table():
    recorded = data(
        entry(1, FIRST, (0, 0), rir=None, duration_seconds=30),
        entry(2, SECOND, (0, 0), rir=None, duration_seconds=40),
        deload=frozenset({201}),
    )
    app = exercise_app(recorded, "Latest comparison")
    assert any("Deload work" in item.value for item in app.info)
    assert app.dataframe[0].value.iloc[0, 2] == "60 kg × 40 s"
    assert not app.metric
    mixed = data(entry(1, FIRST), entry(2, SECOND, (0, 0), rir=None, duration_seconds=40))
    app = exercise_app(mixed, "Latest comparison")
    assert "8 reps" in app.dataframe[0].value.iloc[0, 1]
    assert "40 s" in app.dataframe[0].value.iloc[0, 2]


def test_invalid_latest_quantity_is_rendered_without_a_verdict_or_crash():
    # The comparison must remain reachable even when descriptive metrics omit a log.
    recorded = data(entry(1, FIRST), entry(2, SECOND, (None, 8, 8)))
    app = exercise_app(recorded, "Latest comparison")
    assert any("Invalid recorded values" in item.value for item in app.info)
    assert "× ? reps" in app.dataframe[0].value.iloc[0, 2]
    assert not app.metric


def test_strength_panel_uses_cached_session_values_and_ranking_windows():
    recorded = data(
        entry(1, FIRST),
        entry(2, date(2026, 10, 12), (9, 8, 8)),
        entry(3, date(2026, 10, 19), (10, 9, 8)),
        entry(4, SECOND, (11, 10, 9)),
    )
    metrics = compute_exercise_metrics(recorded)
    trend = rank_exercise_progress(metrics).trends[0]
    app = exercise_app(recorded, "Estimated strength")
    assert app.metric[1].value == f"{trend.change_pct:+.2f}%"
    assert app.metric[2].value == "4" and not app.dataframe
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert chart["data"][0]["y"] == [
        point["estimated_1rm"] for point in metrics["per_exercise"][1]["per_session_1rm"]
    ]
    assert not app.caption


@pytest.mark.parametrize("kind", ["bodyweight", "timed", "deload", "mixed_convention"])
def test_ineligible_strength_history_has_no_numeric_estimate(kind):
    old, new = entry(1, FIRST), entry(2, SECOND)
    if kind == "bodyweight":
        old = entry(1, FIRST, weight=0, load=SetLoad("bodyweight", 0, 80))
        new = entry(2, SECOND, weight=0, load=SetLoad("bodyweight", 0, 80))
    elif kind == "timed":
        old = entry(1, FIRST, (0,), rir=None, duration_seconds=30)
        new = entry(2, SECOND, (0,), rir=None, duration_seconds=40)
    elif kind == "mixed_convention":
        new = entry(2, SECOND, load=SetLoad("external", 60))
    recorded = data(old, new, deload=frozenset({101, 201}) if kind == "deload" else frozenset())
    app = exercise_app(recorded, "Estimated strength")
    assert app.info and not app.metric and not app.get("plotly_chart")


def test_single_estimate_has_no_percentage_trend_and_future_results_are_excluded():
    recorded = data(entry(1, FIRST))
    future = entry(2, date(2099, 1, 1), weight=120, load=SetLoad("external", 120))
    recorded = replace(
        recorded,
        sessions=recorded.sessions + [future[0]],
        workout_exercises=recorded.workout_exercises + [future[1]],
        sets=recorded.sets + list(future[2]),
    )
    app = exercise_app(recorded, "Estimated strength")
    assert [item.value for item in app.metric] == ["76 kg", "—", "1"]


def test_timed_comparison_uses_total_seconds_without_rir():
    app = exercise_app(
        data(
            entry(1, FIRST, (0, 0), rir=None, duration_seconds=30),
            entry(2, SECOND, (0, 0), rir=None, duration_seconds=40),
        ),
        "Latest comparison",
    )
    assert app.metric[0].label == "Seconds vs previous" and app.metric[0].value == "+20"
    assert "RIR" not in app.dataframe[0].value.iloc[0, 2]


def test_exercise_sections_and_shared_period_survive_navigation(
    schedule_data, sample_input, sets_dataframe
):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert app.dataframe and len(app.get("plotly_chart")) == 2
    assert "08 May 2026" in app.dataframe[0].value.columns[-1]
    select_analysis_tab(app, "Progress")
    select_analysis_tab(app, "Exercises")
    assert [item.value for item in app.subheader] == [
        "Recorded history",
        "Estimated strength",
        "Latest comparison",
    ]
    app.button(key="nav_Overview").click().run()
    app.button(key="nav_Analysis").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="analysis_month").value == "2026-05"
    assert app.dataframe and len(app.get("plotly_chart")) == 2
    assert len([item for item in app.selectbox if item.key == "analysis_month"]) == 1
    assert not any(item.label == "Exercise view" for item in app.selectbox)


def test_overview_history_link_opens_exercise_and_full_period():
    app = AppTest.from_string("""
import streamlit as st
from ui.training_insights_view import _open_exercise_history
st.button('Open history', on_click=_open_exercise_history, args=(1,))
""")
    app.run().button[0].click().run()
    assert not app.exception
    assert app.session_state["analysis_tab"] == "Exercises"
    assert app.session_state["analysis_recorded_exercise"] == 1
    assert app.session_state["analysis_period_value"] == "All time"
