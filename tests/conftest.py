from datetime import date, time

import pandas as pd
import pytest

from metrics.input import MetricsInput
from models.body_composition import BodyComposition
from models.body_measurement import BodyMeasurement
from models.exercise import Exercise
from models.exercise_muscle_target import ExerciseMuscleTarget
from models.workout_exercise import WorkoutExercise
from models.workout_session import WorkoutSession
from models.workout_set import WorkoutSet


@pytest.fixture
def sample_input() -> MetricsInput:
    return MetricsInput(
        sessions=[
            WorkoutSession(1, date(2026, 5, 1), time(10, 0), time(11, 0)),
            WorkoutSession(2, date(2026, 5, 8), time(23, 30), time(0, 30)),
            WorkoutSession(3, date(2026, 4, 20), None, None),
        ],
        workout_exercises=[
            WorkoutExercise(101, 1, 1),
            WorkoutExercise(102, 2, 1),
            WorkoutExercise(103, 3, 2),
        ],
        sets=[
            WorkoutSet(101, 1, 10, 100.0, 2),
            WorkoutSet(101, 2, 8, 110.0, 1),
            WorkoutSet(102, 1, 10, 105.0, 0),
            WorkoutSet(102, 2, 8, 115.0, 1),
            WorkoutSet(103, 1, 12, 60.0, 3),
        ],
        exercises=[
            Exercise(1, "Bench Press", None, "Chest"),
            Exercise(2, "Row", None, "Back"),
        ],
        exercise_muscle_targets=[
            ExerciseMuscleTarget(1, "Chest", "Pectoralis", "primary", 1.0),
            ExerciseMuscleTarget(1, "Triceps", "Triceps brachii", "secondary", 0.5),
            ExerciseMuscleTarget(2, "Back", "Latissimus", "primary", 1.0),
        ],
        muscle_groups=["Chest", "Triceps", "Back"],
        body_measurements=[
            BodyMeasurement(date(2026, 4, 1), "waist", 82.0),
            BodyMeasurement(date(2026, 4, 1), "chest", 101.0),
            BodyMeasurement(date(2026, 5, 1), "waist", 80.0),
            BodyMeasurement(date(2026, 5, 1), "chest", 104.0),
            BodyMeasurement(date(2026, 5, 1), "thigh", 60.0),
            BodyMeasurement(date(2026, 5, 1), "biceps", 38.0),
        ],
        body_composition=[
            BodyComposition(date(2026, 4, 1), 80.0, 35.0, 16.0, 48.0, 20.0, "scale"),
            BodyComposition(date(2026, 5, 1), 82.0, 37.0, 15.5, 49.0, 18.9, "scale"),
        ],
    )


@pytest.fixture
def sets_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"session_id": 1, "session_date": "2026-05-01", "exercise_name": "Bench Press"},
            {"session_id": 2, "session_date": "2026-05-08", "exercise_name": "Bench Press"},
            {"session_id": 3, "session_date": "2026-04-20", "exercise_name": "Row"},
        ]
    )
