import pandas as pd

def build_exercises_df(exercises_metrics: dict, sets_df) -> pd.DataFrame:
    per_exercise = exercises_metrics.get("per_exercise", {})
    rows = []
    for exercise_id, m in per_exercise.items():
        rows.append({
            "exercise_id": exercise_id,
            "exercise_name": m["exercise_name"],
            "total_sets": m["total_sets"],
            "total_reps": m["total_reps"],
            "total_volume": m["total_volume"],
            "avg_weight": m["avg_weight"],
            "max_weight": m["max_weight"],
            "estimated_1rm_max": m["estimated_1rm_max"],
            "estimated_1rm_avg": m["estimated_1rm_avg"],
            "avg_rir": m["avg_rir"],
            "sets_to_failure": m["sets_to_failure"],
            "sessions_count": m["sessions_count"],
            "avg_sets_per_session": m["avg_sets_per_session"],
        })
    
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    
    # --- rounding numeric columns for UI ---
    round_cols = ["avg_weight", "max_weight", "estimated_1rm_max", "estimated_1rm_avg", "avg_rir", "avg_sets_per_session"]
    df[round_cols] = df[round_cols].round(2)
    df = df.sort_values("total_volume", ascending=False).reset_index(drop=True)
    
    return df
