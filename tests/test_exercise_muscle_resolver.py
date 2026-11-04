import pytest

from db.exercise_muscle_resolver import resolve_exercise


@pytest.mark.parametrize("name, muscle", [
    ("Wrist Curl", "Wrist flexors"),
    ("Behind-the-back Barbell Wrist Curl", "Wrist flexors"),
    ("Reverse Wrist Curl", "Wrist extensors"),
    ("Cable Reverse Wrist Curl", "Wrist extensors"),
])
def test_wrist_curls_use_forearms_without_crediting_biceps(name, muscle):
    result = resolve_exercise(name)
    assert result.body_part == "Forearms"
    assert result.category == "Pull"
    assert len(result.targets) == 1
    target = result.targets[0]
    assert (target.muscle_group, target.role, target.set_factor) == ("Forearms", "primary", 1.0)
    assert target.muscle_name.startswith(muscle)


def test_dead_hang_uses_local_grip_rule_instead_of_web_snippets(monkeypatch):
    def unexpected_web(*args):
        pytest.fail("Known dead hangs must not depend on web-snippet classification")
    monkeypatch.setattr("db.exercise_muscle_resolver._resolve_from_web", unexpected_web)
    result = resolve_exercise("Dead hang", allow_web=True)
    assert result.body_part == "Forearms"
    targets = {target.muscle_group: target for target in result.targets}
    assert set(targets) == {"Forearms", "Shoulders", "Back"}
    assert targets["Forearms"].role == "primary"
    assert "Finger flexors" in targets["Forearms"].muscle_name
    assert all(targets[group].role == "stabilizer" for group in ("Shoulders", "Back"))


def test_regular_elbow_curl_remains_a_biceps_exercise():
    result = resolve_exercise("Barbell Curl")
    assert result.body_part == "Biceps"
    assert next(target for target in result.targets if target.role == "primary").muscle_group == "Biceps"


def test_resolve_pallof_press_with_rotation_uses_specific_core_rule():
    result = resolve_exercise("Pallof Press with Rotation")

    assert result is not None
    assert result.category == "Push"
    assert result.body_part == "Obliques"
    targets = {target.muscle_group: target for target in result.targets}
    assert set(targets) == {
        "Obliques",
        "Abs",
        "Lower Back",
        "Back",
        "Shoulders",
        "Glutes",
    }
    assert targets["Obliques"].role == "primary"
    assert targets["Abs"].role == "primary"
    assert all(
        targets[group].role == "stabilizer"
        for group in ("Lower Back", "Back", "Shoulders", "Glutes")
    )
    assert "User-provided Pallof press" in targets["Obliques"].source_note


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
