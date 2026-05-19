from datetime import date

import pandas as pd

from ui.body_parts_view import BodyPartsView, _bar_fig, _data_signature
from ui.utils.data_filter import filter_data_by_month
from ui.utils.exercise_matcher import normalize
from ui.utils.muscle_tags import resolve_muscle_tag
from ui.utils.ui_helpers import format_number


def test_filter_data_by_month_filters_related_domain_objects(sample_input, sets_dataframe):
    filtered_input, filtered_df = filter_data_by_month(
        sample_input,
        sets_dataframe,
        "2026-05",
    )

    assert [session.session_id for session in filtered_input.sessions] == [1, 2]
    assert {we.workout_exercise_id for we in filtered_input.workout_exercises} == {101, 102}
    assert {workout_set.workout_exercise_id for workout_set in filtered_input.sets} == {101, 102}
    assert list(filtered_df["session_id"]) == [1, 2]


def test_filter_data_by_month_all_time_returns_original_objects(sample_input, sets_dataframe):
    filtered_input, filtered_df = filter_data_by_month(
        sample_input,
        sets_dataframe,
        "All time",
    )

    assert filtered_input is sample_input
    assert filtered_df is sets_dataframe


def test_simple_ui_helpers_are_deterministic():
    assert normalize(" Bench-Press! ") == "benchpress"
    assert resolve_muscle_tag(" chest ") == ("Chest", "chest")
    assert resolve_muscle_tag(None) == ("Other", "other")
    assert format_number(1234.567, 1) == "1\u202f234.6"
    assert format_number(None) == "—"
    assert format_number("bad") == "—"


def test_body_parts_view_builds_weighted_bodypart_dataframe():
    metrics = {
        "per_exercise": {
            1: {
                "body_part": "Chest",
                "muscle_targets": [
                    {"muscle_group": "Chest", "set_factor": 1.0},
                    {"muscle_group": "Triceps", "set_factor": 0.5},
                ],
                "total_sets": 4,
                "total_volume": 4000,
                "estimated_1rm_avg": 120.0,
                "per_session_1rm": [{"date": date(2026, 5, 1)}],
            },
            2: {
                "body_part": "Back",
                "muscle_targets": [],
                "total_sets": 2,
                "total_volume": 1000,
                "estimated_1rm_avg": 90.0,
                "per_session_1rm": [{"date": date(2026, 5, 2)}],
            },
        }
    }

    body_df = BodyPartsView(metrics, "2026-05")._build_bodypart_df()

    assert list(body_df["Body Part"]) == ["Chest", "Triceps", "Back"]
    assert body_df.loc[body_df["Body Part"] == "Triceps", "Total_Sets"].item() == 2
    assert body_df.loc[body_df["Body Part"] == "Chest", "Sessions"].item() == 1


def test_body_parts_chart_helpers_return_stable_outputs():
    body_df = pd.DataFrame(
        [
            {"Body Part": "Chest", "Total_Sets": 4.0, "Total_Volume": 4000.0, "Sessions": 1, "Avg_1RM": 120.0},
            {"Body Part": "Back", "Total_Sets": 2.0, "Total_Volume": 1000.0, "Sessions": 1, "Avg_1RM": 90.0},
        ]
    )

    assert _data_signature(body_df) == _data_signature(body_df.sample(frac=1))
    assert _bar_fig(body_df, "Total_Volume", "Volume (kg)").data[0].orientation == "h"
