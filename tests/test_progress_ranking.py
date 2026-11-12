"""Early/late windows, honest exclusions and disjoint signed ranking groups."""

from dataclasses import FrozenInstanceError
from datetime import date, timedelta

import pytest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.progress_ranking import rank_exercise_progress, ranking_groups
from models.set_load import SetLoad
from test_load_analysis import source


def metrics(values, *, guard=1):
    return {
        "per_exercise": {
            1: {
                "exercise_name": "Bench Press",
                "strength_trend_1rm": guard,
                "per_session_1rm": [
                    {"estimated_1rm": value, "date": date(2026, 5, 1) + timedelta(days=7 * index)}
                    for index, value in enumerate(values)
                ],
            }
        }
    }


@pytest.mark.parametrize(
    "count,window,baseline,current",
    [
        (2, 1, 100, 110),
        (3, 1, 100, 120),
        (4, 2, 105, 125),
        (5, 2, 105, 135),
        (6, 3, 110, 140),
        (7, 3, 110, 150),
    ],
)
def test_windows_are_equal_non_overlapping_and_use_at_most_three_sessions(
    count, window, baseline, current
):
    report = rank_exercise_progress(metrics([100 + 10 * index for index in range(count)]))
    item = report.trends[0]
    assert (item.window, item.baseline, item.current, item.sessions) == (
        window,
        baseline,
        current,
        count,
    )
    assert item.change_pct == round((current / baseline - 1) * 100, 2)
    assert not set(item.baseline_dates) & set(item.current_dates)
    with pytest.raises(FrozenInstanceError):
        item.baseline = 999


@pytest.mark.parametrize(
    "values,guard",
    [
        ([100], 1),
        ([100, 110], None),
        ([0, 100], 1),
        ([None, 100], 1),
        ([float("nan"), 100], 1),
    ],
)
def test_unavailable_or_invalid_history_never_becomes_a_zero_change(values, guard):
    result = rank_exercise_progress(metrics(values, guard=guard))
    assert not result.trends
    assert result.unavailable_exercise_ids == (1,)


def test_existing_load_guards_keep_bodyweight_and_changed_conventions_out(sample_input):
    for observations in [
        [(SetLoad("bodyweight", 0, 80), 8), (SetLoad("bodyweight", 0, 80), 10)],
        [(60.0, 8), (SetLoad("external", 60), 10)],
    ]:
        result = rank_exercise_progress(
            compute_exercise_metrics(source(sample_input, observations))
        )
        assert not result.trends and result.unavailable_exercise_ids == (1,)


def test_timed_holds_are_separate_and_require_unchanged_known_total_load(sample_input):
    load = SetLoad("bodyweight", 0, 80)
    result = rank_exercise_progress(
        compute_exercise_metrics(source(sample_input, [(load, 40), (load, 50)], timed=True))
    )
    assert len(result.trends) == 1
    assert result.trends[0].measure == "Hold time"
    assert result.trends[0].change_pct == 25
    for changed in [SetLoad("bodyweight", 0, 82), SetLoad("bodyweight", 0, None)]:
        result = rank_exercise_progress(
            compute_exercise_metrics(source(sample_input, [(load, 40), (changed, 50)], timed=True))
        )
        assert not result.trends


def test_groups_show_five_largest_increases_and_five_lowest_changes_without_padding():
    combined = {"per_exercise": {}}
    for eid in range(1, 18):
        item = metrics([100, 100 + eid if eid < 9 else 100 - (eid - 8)])["per_exercise"][1]
        combined["per_exercise"][eid] = {**item, "exercise_name": f"Exercise {eid}"}
    report = rank_exercise_progress(combined)
    top, bottom = ranking_groups(report.trends)
    assert [item.exercise_id for item in top] == [8, 7, 6, 5, 4]
    assert [item.exercise_id for item in bottom] == [17, 16, 15, 14, 13]
    assert not {item.exercise_id for item in top} & {item.exercise_id for item in bottom}
    top, bottom = ranking_groups(rank_exercise_progress(metrics([100, 110])).trends)
    assert len(top) == 1 and not bottom
    top, bottom = ranking_groups(rank_exercise_progress(metrics([100, 100])).trends)
    assert not top and bottom[0].change_pct == 0


def test_missing_effort_and_deloads_do_not_create_strength_estimates(sample_input):
    from dataclasses import replace

    data = source(sample_input, [(60.0, 8), (65.0, 10)])
    missing = replace(data, sets=[replace(item, rir=None) for item in data.sets])
    assert not rank_exercise_progress(compute_exercise_metrics(missing)).trends
    deload = replace(data, deload_exercise_ids=frozenset({200}))
    assert not rank_exercise_progress(compute_exercise_metrics(deload)).trends


def test_chart_keeps_numeric_catalog_ids_in_rank_order_with_equal_row_spacing():
    from dataclasses import replace

    from ui.progress_ranking_view import ranking_chart

    trend = rank_exercise_progress(metrics([100, 110])).trends[0]
    items = (
        replace(trend, exercise_id=91, name="A long exercise name " * 5, change_pct=30),
        replace(trend, exercise_id=2, change_pct=10),
        replace(trend, exercise_id=500, change_pct=5),
    )
    chart = ranking_chart(items)
    assert chart.layout.yaxis.type == "category"
    assert list(chart.layout.yaxis.categoryarray) == ["91", "2", "500"]
    assert list(chart.data[0].x) == [30, 10, 5]
