from db.exercise_muscle_resolver import resolve_exercise


def test_resolve_hanging_leg_raise_uses_specific_rule():
    result = resolve_exercise("Hanging Leg Raise")

    assert result is not None
    assert result.category == "Push"
    assert result.body_part == "Abs"
    targets = {target.muscle_group: target for target in result.targets}
    assert set(targets) == {"Abs", "Obliques", "Forearms", "Shoulders", "Back"}
    assert targets["Abs"].role == "primary"
    assert targets["Forearms"].role == "stabilizer"
    assert targets["Shoulders"].role == "stabilizer"
    assert targets["Back"].role == "stabilizer"


def test_resolve_regular_leg_raise_still_uses_general_abs_rule():
    result = resolve_exercise("Lying Leg Raise")

    assert result is not None
    assert result.category == "Push"
    assert result.body_part == "Abs"
    assert {target.muscle_group for target in result.targets} == {"Abs", "Obliques"}
