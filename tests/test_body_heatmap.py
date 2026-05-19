from ui.utils.body_heatmap import _excluded_overlay_mask


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
