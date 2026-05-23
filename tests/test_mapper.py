from datetime import date, time

from mapper import (
    map_body_composition,
    map_body_measurement,
    map_exercise,
    map_exercise_muscle_target,
    map_workout_exercise,
    map_workout_session,
    map_workout_set,
)


def test_training_row_mappers_return_domain_models():
    session = map_workout_session(
        {
            "session_id": 1,
            "session_date": date(2026, 5, 1),
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }
    )
    workout_exercise = map_workout_exercise(
        {"workout_exercise_id": 10, "session_id": 1, "exercise_id": 2}
    )
    workout_set = map_workout_set(
        {
            "workout_exercise_id": 10,
            "set_number": 1,
            "repetitions": 8,
            "weight": 100.0,
            "duration_seconds": None,
            "rir": 1,
        }
    )

    assert session.session_id == 1
    assert workout_exercise.exercise_id == 2
    assert workout_set.weight == 100.0
    assert workout_set.duration_seconds is None


def test_exercise_and_muscle_mappers_return_expected_values():
    exercise = map_exercise(
        {"exercise_id": 2, "exercise_name": "Row", "body_part": "Back"}
    )
    target = map_exercise_muscle_target(
        {
            "exercise_id": 2,
            "muscle_group": "Back",
            "muscle_name": "Latissimus",
            "role": "primary",
            "set_factor": "1.0",
        }
    )
    assert exercise.name == "Row"
    assert target.set_factor == 1.0


def test_body_measurement_mapper_flattens_non_empty_columns():
    measurements = map_body_measurement(
        {
            "measurement_date": date(2026, 5, 1),
            "chest": 104.0,
            "waist": None,
            "abdomen": None,
            "hips": None,
            "thigh": 60.0,
            "calf": None,
            "biceps": 38.0,
        }
    )

    assert [m.measurement_type for m in measurements] == ["chest", "thigh", "biceps"]
    assert [m.value for m in measurements] == [104.0, 60.0, 38.0]


def test_body_composition_mapper_uses_database_column_names():
    entry = map_body_composition(
        {
            "measurement_date": date(2026, 5, 1),
            "weight": 82.0,
            "muscle_mass": 37.0,
            "fat_mass": 15.5,
            "water_mass": 49.0,
            "body_fat_percentage": 18.9,
            "method": "scale",
        }
    )

    assert entry.weight == 82.0
    assert entry.fat_percentage == 18.9
