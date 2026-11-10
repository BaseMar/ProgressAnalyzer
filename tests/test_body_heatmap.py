import pandas as pd
from streamlit.testing.v1 import AppTest

from metrics.muscle_distribution import build_weekly_distribution, status_from_plan
from ui.utils.body_heatmap import (
    BODY_IMAGE_PATH,
    MUSCLE_GROUP_SEEDS,
    _body_fill_mask,
    _excluded_overlay_mask,
    _mask_from_seeds,
)


def test_excluded_overlay_mask_covers_hands_and_feet():
    mask = _excluded_overlay_mask((1086, 1448))

    excluded_points = [
        (260, 550),
        (630, 550),
        (800, 550),
        (1160, 550),
        (370, 990),
        (535, 990),
        (890, 990),
        (1085, 990),
    ]
    included_points = [
        (282, 426),
        (614, 426),
        (384, 769),
        (1040, 796),
    ]

    assert all(mask[y, x] for x, y in excluded_points)
    assert not any(mask[y, x] for x, y in included_points)


def test_forearm_inner_panels_are_colored_as_forearms_not_obliques():
    fill_mask = _body_fill_mask(BODY_IMAGE_PATH.stat().st_mtime_ns)
    forearms_mask = _mask_from_seeds(fill_mask, MUSCLE_GROUP_SEEDS["Forearms"])
    obliques_mask = _mask_from_seeds(fill_mask, MUSCLE_GROUP_SEEDS["Obliques"])

    inner_forearm_points = [
        (303, 434),
        (593, 434),
    ]

    assert all(forearms_mask[y, x] for x, y in inner_forearm_points)
    assert not any(obliques_mask[y, x] for x, y in inner_forearm_points)


def test_heatmap_seeds_cover_front_thigh_and_upper_oblique_panels():
    fill_mask = _body_fill_mask(BODY_IMAGE_PATH.stat().st_mtime_ns)
    legs_mask = _mask_from_seeds(fill_mask, MUSCLE_GROUP_SEEDS["Legs"])
    obliques_mask = _mask_from_seeds(fill_mask, MUSCLE_GROUP_SEEDS["Obliques"])

    front_thigh_points = [
        (363, 680),
        (533, 680),
    ]
    upper_oblique_points = [
        (390, 335),
        (510, 335),
    ]

    assert all(legs_mask[y, x] for x, y in front_thigh_points)
    assert all(obliques_mask[y, x] for x, y in upper_oblique_points)


def test_map_compares_plan_independently_of_reference():
    assert status_from_plan(8.0, 12.0) == "under"
    assert status_from_plan(12.5, 12.0) == "on_target"
    assert status_from_plan(14.0, 12.0) == "over"
    assert status_from_plan(6.0, 6.0) == "on_target"
    assert status_from_plan(25.0, 25.0) == "on_target"


def test_missing_plan_is_neutral_and_zero_means_not_planned():
    assert status_from_plan(8.0, None) == "no_range"
    assert status_from_plan(12.0, None) == "no_range"
    assert status_from_plan(25.0, None) == "no_range"
    assert status_from_plan(0.0, 0.0) == "not_planned"
    assert status_from_plan(5.0, 0.0) == "unplanned"


def test_build_heatmap_df_reports_target_percentage():
    body_df = pd.DataFrame(
        [
            {"Body Part": "Back", "Total_Sets": 21.0},
        ]
    )

    result = build_weekly_distribution(body_df, period_weeks=3.0, weekly_targets={"Back": 20.0})

    row = result.loc[result["Body Part"] == "Back"].iloc[0]
    assert row["Sets / Week"] == 7.0
    assert row["Target %"] == 35.0
    assert row["Status"] == "under"


def test_heatmap_renders_accessible_iframe_with_escaped_labels():
    app = AppTest.from_string(
        """
import pandas as pd
from metrics.muscle_distribution import build_weekly_distribution
from ui.utils.body_heatmap import render_body_heatmap
frame = pd.DataFrame([
    {"Body Part": "Back", "Total_Sets": 12.0},
    {"Body Part": "<script>alert(1)</script>", "Total_Sets": 1.0},
])
heatmap = build_weekly_distribution(frame, period_weeks=1, weekly_targets={"Back": 12})
render_body_heatmap(heatmap, period_weeks=1, period_label="This week")
""",
        default_timeout=30,
    ).run()
    assert not app.exception
    iframe = app.get("iframe")[0].proto
    assert iframe.alt == "Muscle allocation compared with the training plan"
    assert 'class="body-image"' in iframe.srcdoc
    assert 'class="body-overlay"' in iframe.srcdoc
    assert "data:image/png;base64," in iframe.srcdoc
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in iframe.srcdoc.lower()
    assert "<script>alert(1)</script>" not in iframe.srcdoc.lower()
