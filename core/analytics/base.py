from typing import Iterable
import pandas as pd
import numpy as np

REQUIRED_SET_COLS = {"SessionDate", "ExerciseName", "Weight", "Repetitions", "SetNumber"}

def require_columns(df: pd.DataFrame, cols: Iterable[str]):
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError(f"Brakuje wymaganych kolumn: {missing}")

def compute_est_1rm(weight: float, reps: int) -> float:
    # Epley formula (często używana): 1RM = w * (1 + r/30)
    if reps <= 0:
        return 0.0
    return weight * (1 + reps / 30)

def pct_change(current: float, previous: float) -> float:
    if previous == 0 or previous is None:
        return 0.0
    return (current - previous) / previous * 100.0

def add_volume_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Volume" not in df.columns:
        df = df.copy()
        df["Volume"] = df["Weight"] * df["Repetitions"]
    return df
