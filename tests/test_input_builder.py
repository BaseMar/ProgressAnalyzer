from datetime import date, time

import pandas as pd

from metrics.input_builder import MetricsInputBuilder


def test_metrics_input_builder_translates_dataframes_to_domain_input():
    metrics_input = MetricsInputBuilder.build(
        sessions_df=pd.DataFrame(
            [
                {
                    "session_id": 1,
                    "session_date": date(2026, 5, 1),
                    "start_time": time(10, 0),
                    "end_time": time(11, 0),
                }
            ]
        ),
        exercises_df=pd.DataFrame(
            [{"exercise_id": 1, "exercise_name": "Bench Press", "body_part": "Chest"}]
        ),
        sets_df=pd.DataFrame(
            [
                {
                    "workout_exercise_id": 101,
                    "session_id": 1,
                    "exercise_id": 1,
                    "set_number": 1,
                    "repetitions": 10,
                    "weight": 100.0,
                    "rir": 2,
                }
            ]
        ),
        body_measurements_df=pd.DataFrame(
            [
                {
                    "measurement_date": date(2026, 5, 1),
                    "chest": 104.0,
                    "waist": 80.0,
                }
            ]
        ),
        body_composition_df=pd.DataFrame(
            [
                {
                    "measurement_date": date(2026, 5, 1),
                    "weight": 82.0,
                    "muscle_mass": 37.0,
                    "fat_mass": 15.5,
                    "water_mass": 49.0,
                    "body_fat_percentage": 18.9,
                    "method": "scale",
                }
            ]
        ),
    )

    assert metrics_input.sessions[0].session_date == date(2026, 5, 1)
    assert metrics_input.workout_exercises[0].workout_exercise_id == 101
    assert metrics_input.exercises[0].body_part == "Chest"
    assert [m.measurement_type for m in metrics_input.body_measurements] == [
        "chest",
        "waist",
    ]
