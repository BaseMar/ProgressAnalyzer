"""Weekly normalization and plan comparisons, independent of research thresholds."""

import pandas as pd

from metrics.muscle_volume import BODY_PART_ORDER


def status_from_plan(sets_per_week, target):
    if target is None:
        return "no_range"
    if target == 0:
        return "unplanned" if sets_per_week > 0 else "not_planned"
    if sets_per_week < target * 0.9:
        return "under"
    if sets_per_week > target * 1.1:
        return "over"
    return "on_target"


def build_weekly_distribution(body_df, period_weeks, weekly_targets=None):
    source = body_df.copy()
    source["Body Part"] = source["Body Part"].astype(str).str.strip().str.title()
    # Older callers can supply only weighted totals; do not invent raw role counts.
    if "Direct_Sets" not in source and "Indirect_Sets" not in source:
        source["Unclassified_Sets"] = source["Total_Sets"]
    fields = ["Total_Sets", "Direct_Sets", "Indirect_Sets", "Unclassified_Sets"]
    source = source.reindex(columns=["Body Part", *fields], fill_value=0.0)
    source = source.groupby("Body Part")[fields].sum()
    seen = set(source.index) | set(weekly_targets or {})
    parts = [*BODY_PART_ORDER, *sorted(seen.difference(BODY_PART_ORDER))]
    weeks = max(float(period_weeks), 1.0)
    rows = []
    for part in parts:
        counts = source.loc[part] if part in source.index else dict.fromkeys(fields, 0.0)
        total = float(counts["Total_Sets"])
        roles_known = counts["Unclassified_Sets"] == 0
        per_week = total / weeks
        target = weekly_targets.get(part, 0.0) if weekly_targets is not None else None
        rows.append(
            {
                "Body Part": part,
                "Target": target,
                "Total Sets": total,
                "Direct / week": float(counts["Direct_Sets"]) / weeks if roles_known else None,
                "Indirect / week": float(counts["Indirect_Sets"]) / weeks if roles_known else None,
                "Sets / Week": per_week,
                "Target %": per_week / target * 100 if target is not None and target > 0 else None,
                "Status": status_from_plan(per_week, target),
            }
        )
    return pd.DataFrame(rows)
