import pandas as pd


def build_body_parts_df(exercises_metrics: dict) -> pd.DataFrame:
        """
        Aggregate exercise-level metrics into body-part-level metrics.
        """
        per_exercise = exercises_metrics.get("per_exercise", {})
        if not per_exercise:
            return pd.DataFrame()

        rows = []

        for ex in per_exercise.values():
            body_part = ex.get("body_part")
            if body_part is None:
                continue

            rows.append({
                "Body Part": body_part,
                "Exercise": ex["exercise_name"],
                "Sets": ex["total_sets"],
                "Volume": ex["total_volume"],
                "Estimated 1RM": ex["estimated_1rm_max"],
                "Sessions": ex["sessions_count"]})

        df = pd.DataFrame(rows)

        if df.empty:
            return df

        body_df = (df.groupby("Body Part").agg(
                Exercises=("Exercise", "nunique"),
                Total_Sets=("Sets", "sum"),
                Total_Volume=("Volume", "sum"),
                Avg_1RM=("Estimated 1RM", "mean"),
                Sessions=("Sessions", "sum")).reset_index().sort_values("Total_Volume", ascending=False))

        body_df["Avg_1RM"] = body_df["Avg_1RM"].round(2)

        return body_df