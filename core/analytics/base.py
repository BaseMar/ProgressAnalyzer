from typing import Iterable

import numpy as np
import pandas as pd

REQUIRED_SET_COLS = {
    "SessionDate",
    "ExerciseName",
    "Weight",
    "Repetitions",
    "SetNumber",
}


def require_columns(df: pd.DataFrame, cols: Iterable[str]) -> None:
    """Check that required columns are present in the DataFrame.

    Raises ValueError if any required columns are missing.
    """
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def compute_est_1rm(weight, reps) -> pd.Series:
    """Compute estimated one-rep max using Epley formula: 1RM = weight * (1 + reps / 30).

    Sets 1RM to 0 for zero or negative rep counts. Returns a Series.
    """
    weight = pd.Series(weight)
    reps = pd.Series(reps)

    result = weight * (1 + reps / 30)
    result[reps <= 0] = 0

    return result


def pct_change(current: float, previous: float) -> float:
    """Calculate percentage change from previous to current.

    Returns 0.0 if previous is 0 or None.
    """
    if previous == 0 or previous is None:
        return 0.0
    return (current - previous) / previous * 100.0


def add_volume_column(df: pd.DataFrame, overwrite: bool = False) -> pd.DataFrame:
    """Add a Volume column as Weight * Repetitions if not already present.

    Returns a copy of the DataFrame with the Volume column added.
    """
    if "Volume" not in df.columns:
        df = df.copy()
        df["Volume"] = df["Weight"] * df["Repetitions"]
    return df
