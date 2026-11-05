import pandas as pd

from ui.utils.body_heatmap import (
    BODY_IMAGE_PATH,
    MUSCLE_GROUP_SEEDS,
    _build_heatmap_df,
    _body_fill_mask,
    _excluded_overlay_mask,
    _mask_from_seeds,
    _status_from_range,
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
    assert _status_from_range(8.0, 10.0, 12.0, 20.0) == "under"
    assert _status_from_range(12.5, 10.0, 12.0, 20.0) == "on_target"
    assert _status_from_range(14.0, 10.0, 12.0, 20.0) == "over"
    assert _status_from_range(6.0, 10.0, 6.0, 20.0) == "on_target"
    assert _status_from_range(25.0, 10.0, 25.0, 20.0) == "on_target"


def test_missing_plan_uses_reference_but_zero_means_not_planned():
    assert _status_from_range(8.0, 10.0, None, 20.0) == "minimum"
    assert _status_from_range(12.0, 10.0, None, 20.0) == "high"
    assert _status_from_range(25.0, 10.0, None, 20.0) == "above_reference"
    assert _status_from_range(0.0, 10.0, 0.0, 20.0) == "no_range"


def test_build_heatmap_df_reports_target_percentage():
    body_df = pd.DataFrame(
        [
            {"Body Part": "Back", "Total_Sets": 21.0},
        ]
    )

    result = _build_heatmap_df(
        body_df,
        ["Back"],
        {"Back": {"Min": 10.0, "Target": 20.0, "Max": 20.0}},
        period_weeks=3.0,
    )

    row = result.iloc[0]
    assert row["Sets / Week"] == 7.0
    assert row["Target %"] == 35.0
    assert row["Status"] == "under"
