"""Raw role counts, weighted targets, contextual sources and plan-only coloring."""

from dataclasses import replace
from datetime import date

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from metrics.exercise_metrics import compute_exercise_metrics
from metrics.muscle_distribution import build_weekly_distribution
from metrics.muscle_volume import allocation_components, weekly_plan_allocation
from models.exercise_muscle_target import ExerciseMuscleTarget
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft
from test_muscle_volume import open_muscle_distribution, ranges_table
from test_plan_schedule import schedule_data as schedule_data
from ui.body_parts_view import BodyPartsView


@pytest.mark.parametrize(
    "role,factor,expected",
    [
        ("primary", 0.8, (3, 0, 0, 0, 2.4)),
        ("secondary", 0.5, (0, 3, 0, 0, 1.5)),
        ("stabilizer", 0.25, (0, 3, 3, 0, 0.75)),
        (None, 0.4, (0, 0, 0, 3, 1.2)),
    ],
)
def test_role_counts_are_raw_and_factors_are_preserved(role, factor, expected):
    row = allocation_components(3, {"role": role, "set_factor": factor})
    assert tuple(row.values()) == pytest.approx(expected)


def test_plan_and_recorded_allocation_use_identical_roles_and_factors(sample_input):
    targets = [
        ExerciseMuscleTarget(1, group, group, role, factor)
        for group, role, factor in (
            ("Chest", "primary", 1),
            ("Triceps", "secondary", 0.5),
            ("Forearms", "stabilizer", 0.25),
        )
    ]
    source = replace(
        sample_input,
        exercise_muscle_targets=targets,
        workout_exercises=sample_input.workout_exercises[:1],
        sets=sample_input.sets[:1],
    )
    source = replace(
        source,
        sets=[replace(source.sets[0], set_number=index, is_warmup=False) for index in (1, 2, 3)],
    )
    draft = TrainingPlanDraft(
        "Test", date.today(), (TrainingDay("Day", 0, (PlannedExercise(1, 3, 6, 10),)),)
    )
    allocation, missing = weekly_plan_allocation(draft, source)
    actual = (
        BodyPartsView(compute_exercise_metrics(source))._build_bodypart_df().set_index("Body Part")
    )
    assert not missing
    for group, fields in allocation.items():
        for field, value in fields.items():
            assert actual.loc[group, field] == value
    assert allocation["Forearms"]["Indirect_Sets"] == 3
    assert allocation["Forearms"]["Total_Sets"] == 0.75


def test_raw_and_weighted_weekly_values_share_one_period_denominator():
    frame = pd.DataFrame(
        [
            {
                "Body Part": "Biceps",
                "Total_Sets": 10.0,
                "Direct_Sets": 6.0,
                "Indirect_Sets": 8.0,
                "Stabilizer_Sets": 0.0,
                "Unclassified_Sets": 0.0,
            }
        ]
    )
    row = (
        build_weekly_distribution(frame, 2.0, {"Biceps": 12.0}).set_index("Body Part").loc["Biceps"]
    )
    assert row["Sets / Week"] == 5
    assert row["Target %"] == pytest.approx(100 * 5 / 12)
    assert row["Status"] == "under"


def test_normalized_muscle_names_merge_instead_of_losing_exposure():
    frame = pd.DataFrame(
        [
            {"Body Part": " chest ", "Total_Sets": 2.0, "Direct_Sets": 2.0},
            {"Body Part": "Chest", "Total_Sets": 3.0, "Direct_Sets": 3.0},
        ]
    )
    row = build_weekly_distribution(frame, 1.0, {"Chest": 5.0}).set_index("Body Part").loc["Chest"]
    assert row["Sets / Week"] == 5
    assert row["Status"] == "on_target"


def test_large_plan_target_is_not_clamped_to_a_research_threshold():
    frame = pd.DataFrame([{"Body Part": "Biceps", "Total_Sets": 30.0}])
    row = (
        build_weekly_distribution(frame, 1.0, {"Biceps": 30.0}).set_index("Body Part").loc["Biceps"]
    )
    assert row["Status"] == "on_target"
    assert row["Target %"] == 100
    assert "Min" not in row and "Max" not in row


def test_missing_target_never_uses_a_research_threshold_as_a_color():
    frame = pd.DataFrame([{"Body Part": "Biceps", "Total_Sets": 100.0}])
    result = build_weekly_distribution(frame, 1.0)
    assert result["Status"].eq("no_range").all()
    assert result["Target %"].isna().all()


def test_untrained_muscle_in_plan_gets_target_and_zero_actual():
    frame = pd.DataFrame(columns=["Body Part", "Total_Sets"])
    row = (
        build_weekly_distribution(frame, 1.0, {"Biceps": 6.0}).set_index("Body Part").loc["Biceps"]
    )
    assert row["Target"] == 6 and row["Sets / Week"] == 0
    assert row["Status"] == "under"


def test_table_contains_only_the_four_essential_fields(schedule_data, sample_input, sets_dataframe):
    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)
    table = app.dataframe[0].value
    assert list(table.columns) == ["Body Part", "Target", "Recorded / week", "Target %"]
    assert [item.label for item in app.expander] == ["Filters"]
    assert not any(item.key == "muscle_reference_group" for item in app.selectbox)
    assert not any("doi.org" in item.value or "Counting" in item.value for item in app.markdown)
    assert (
        ranges_table(app).loc["Triceps", "Recorded / week"]
        == ranges_table(app).loc["Chest", "Recorded / week"] * 0.5
    )
    app.radio(key="analysis_muscle_view").set_value("Set allocation").run()
    assert not app.exception and not app.error
    assert len(app.get("plotly_chart")) == 1
    assert list(app.dataframe[0].value.columns) == list(table.columns)
    assert ranges_table(app).loc["Chest", "Target"] == 3


def test_missing_roles_do_not_add_technical_columns_or_change_weighted_total():
    app = AppTest.from_string(
        """
from ui.body_parts_view import BodyPartsView
BodyPartsView({"per_exercise": {1: {"body_part": "Chest", "total_sets": 4, "total_volume": 0,
    "muscle_targets": [{"muscle_group": "Chest", "set_factor": 0.5}]}}}).render()
""",
        default_timeout=30,
    ).run()
    assert not app.exception and not app.error
    table = app.dataframe[0].value.set_index("Body Part")
    assert table.loc["Chest", "Recorded / week"] == 2
    assert "Unclassified / week" not in table
    assert not app.expander
