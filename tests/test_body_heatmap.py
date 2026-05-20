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
