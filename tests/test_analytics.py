import numpy as np
import pandas as pd

from core.analytics.base import compute_est_1rm
from core.analytics.exercise import ExerciseAnalytics
from core.analytics.muscles import MuscleAnalytics


def test_compute_est_1rm_basic():
    w = pd.Series([100, 80, 60])
    r = pd.Series([1, 5, 10])
    res = compute_est_1rm(w, r)
    # epley: 100*(1+1/30)=103.333..., 80*(1+5/30)=93.333..., 60*(1+10/30)=80
    assert round(float(res.iloc[0]), 3) == round(100 * (1 + 1 / 30), 3)
    assert round(float(res.iloc[1]), 3) == round(80 * (1 + 5 / 30), 3)
    assert round(float(res.iloc[2]), 3) == round(60 * (1 + 10 / 30), 3)


def test_exercise_compute_session_summary_correctness():
    df = pd.DataFrame(
        {
            "SessionDate": ["2025-11-01", "2025-11-01", "2025-11-08"],
            "ExerciseName": ["Bench", "Bench", "Bench"],
            "Weight": [100, 90, 105],
            "Repetitions": [1, 3, 1],
            "SetNumber": [1, 2, 1],
        }
    )
    ea = ExerciseAnalytics(df)
    ex_df = ea.filter_exercise("Bench")
    summary = ea.compute_session_summary(ex_df)
    # should have two session dates
    assert summary.shape[0] == 2
    # check columns exist
    assert "Est1RM" in summary.columns
    assert "TotalVolume" in summary.columns


def test_muscle_groups_summary_minimal():
    df = pd.DataFrame(
        {
            "SessionDate": ["2025-10-01", "2025-10-08", "2025-10-15", "2025-10-22"],
            "BodyPart": ["Chest", "Chest", "Back", "Back"],
            "Volume": [500, 600, 300, 400],
            "Intensity": [70, 72, 65, 67],
        }
    )
    ma = MuscleAnalytics(df)
    summary = ma.muscle_groups_summary()
    # expect at least Chest and Back
    parts = set(summary["BodyPart"].tolist())
    assert "Chest" in parts
    assert "Back" in parts
    # check recommended columns exist
    for c in [
        "recommended_min",
        "recommended_max",
        "load_level",
        "trend_pct",
        "assessment",
    ]:
        assert c in summary.columns
