"""Overview indicators stay interpretable without double-counting future work."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from test_plan_adherence import TODAY, example
from metrics.plan_adherence import compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.plan_summary import summarize_plan
from ui.utils.plan_charts import exercise_history_chart, weekly_execution_chart


def test_range_percentage_uses_logged_sets_while_coverage_uses_plan():
    data = example(count=2)
    data = replace(data, recorded=(replace(data.recorded[0], sets=(
        data.recorded[0].sets[0], replace(data.recorded[0].sets[1], repetitions=3),
    )),))
    report = compute_plan_adherence(data, as_of=TODAY)
    performance = compute_plan_performance(data, as_of=TODAY)
    summary = summarize_plan(report, performance)
    assert summary["workout_pct"] == 100
    assert summary["set_pct"] == 200 / 3
    assert summary["range_pct"] == 50
    assert summary["largest_gap"] == ("Upper", 1)
    assert summary["missing_rir"] == 2
    assert summary["weeks"][0]["partial"] == 1


def test_future_workout_is_not_added_to_weekly_chart_or_indicators():
    data = example()
    future = replace(data.workouts[0], slot=replace(data.workouts[0].slot, scheduled_date=TODAY + timedelta(days=14)))
    data = replace(data, workouts=(*data.workouts, future))
    report = compute_plan_adherence(data, as_of=TODAY)
    performance = compute_plan_performance(data, as_of=TODAY)
    summary = summarize_plan(report, performance)
    assert summary["recorded_sets"] == 3
    assert len(summary["weeks"]) == 1
    assert summary["weeks"][0]["complete"] == 1
    fig = weekly_execution_chart(summary["weeks"])
    assert sum(sum(trace.y) for trace in fig.data) == 1


def test_empty_denominators_remain_unknown_not_zero_percent():
    data = replace(example(), workouts=())
    summary = summarize_plan(compute_plan_adherence(data, as_of=TODAY), [])
    assert summary["range_pct"] is None
    assert summary["workout_pct"] is None
    assert summary["set_pct"] is None
    assert summary["weeks"] == []


def test_exercise_chart_shows_previous_context_and_target_band():
    data = example()
    rows = compute_plan_performance(data, as_of=TODAY)
    fig = exercise_history_chart(rows)
    assert len(fig.data) == 2  # Rep values and load share the same observations.
    assert fig.layout.shapes[0].y0 == 6
    assert fig.layout.shapes[0].y1 == 10
    assert list(fig.data[0].y) == [8]
    assert list(fig.data[1].y) == [50]


@pytest.mark.parametrize("point_count", [1, 4])
@pytest.mark.parametrize("load", [0, 50])
def test_target_band_covers_each_session_in_data_coordinates(point_count, load):
    base = compute_plan_performance(example(), as_of=TODAY)[0]
    rows = [dict(base, session_id=index + 1, previous=None,
                 performed_on=base["performed_on"] + timedelta(days=index * 7),
                 sets=tuple(dict(item, weight=load) for item in base["sets"]),
                 target_min=6 + index, target_max=10 + index)
            for index in range(point_count)]
    fig = exercise_history_chart(rows)
    bounds = fig.layout.xaxis.range
    assert bounds == (-0.5, point_count - 0.5)
    assert len(fig.layout.shapes) == point_count
    for index, band in enumerate(fig.layout.shapes):
        assert (band.xref, band.yref) == ("x", "y")
        assert (band.x0, band.x1) == (index - 0.5, index + 0.5)
        assert (band.y0, band.y1) == (rows[index]["target_min"], rows[index]["target_max"])
    if load:
        assert fig.layout.xaxis2.range == bounds
