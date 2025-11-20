from typing import Iterable
import pandas as pd
import numpy as np

REQUIRED_SET_COLS = {"SessionDate", "ExerciseName", "Weight", "Repetitions", "SetNumber"}

def require_columns(df: pd.DataFrame, cols: Iterable[str]):
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError(f"Brakuje wymaganych kolumn: {missing}")

def compute_est_1rm(weight, reps):
    """Liczy wg wzoru Epleya: 1RM = w * (1 + r/30)"""
    weight = pd.Series(weight)
    reps = pd.Series(reps)

    result = weight * (1 + reps / 30)
    result[reps <= 0] = 0

    return result

def pct_change(current: float, previous: float) -> float:
    if previous == 0 or previous is None:
        return 0.0
    return (current - previous) / previous * 100.0

def add_volume_column(df: pd.DataFrame, overwrite: bool=False) -> pd.DataFrame:
    if "Volume" not in df.columns:
        df = df.copy()
        df["Volume"] = df["Weight"] * df["Repetitions"]
    return df
