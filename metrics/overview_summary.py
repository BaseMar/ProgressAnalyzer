"""Observable current decisions, with no global effectiveness score."""
from metrics.training_block import training_block_phase
from models.overview import OverviewConclusion, RecommendationGap, WorkoutFocus


def workout_focus(recommendation):
    """Two useful targets by default; the whole prescription remains reachable."""
    ready = tuple(item for item in recommendation.exercises if item.goals and
                  (item.action != "insufficient_data" or item.reason_code == "manual_start_selected"))
    changes = tuple(item for item in ready if item.action in ("increase_reps", "increase_time", "equalize_weight", "increase_weight", "reduce_weight", "deload")
                    or item.reason_code == "resume_after_deload")
    missing = {}
    for item in recommendation.exercises:
        if (item.action == "insufficient_data" and item.reason_code != "manual_start_selected") or not item.goals:
            missing.setdefault(item.reason_code, []).append(item)
    gaps = tuple(RecommendationGap(len(items), items[0]) for items in missing.values())
    return WorkoutFocus((changes or ready)[:2], len(ready), len(recommendation.exercises), gaps)


def overview_conclusion(report, preview, *, as_of, version):
    if version.draft.effective_from > as_of:
        return OverviewConclusion("Your plan starts soon", f"First planned date: {version.draft.effective_from:%d %b %Y}. Review the upcoming workout below.")
    phase = training_block_phase(as_of, version.draft.progression)
    if phase.phase == "not_started":
        return OverviewConclusion("Your training block starts soon", f"Block starts on {version.draft.progression.block_start:%d %b %Y}. Keep the plan ready below.")
    if phase.phase == "deload":
        return OverviewConclusion("This is your lighter week", f"Deload runs through {phase.cycle_end:%d %b}. Use the lighter prescription; ordinary progression resumes afterwards.", "deload")
    if any(item.code == "below_target_rir" for item in report.annotations):
        return OverviewConclusion("Match the planned reserve first", "At least one recent exercise had less reserve than prescribed. Check the evidence before adding more load.", "attention")
    if preview is None:
        return OverviewConclusion("Review your recent training", "Recent observations are below. Choose an available upcoming workout to see its targets.")
    focus = workout_focus(preview.recommendation)
    if not focus.available:
        return OverviewConclusion("Build the evidence for your next target", "Open the full workout for missing data or plan settings; add another log when a baseline is needed.", "attention")
    if focus.available < focus.total:
        return OverviewConclusion("Your next workout is partly ready", f"{focus.available} of {focus.total} exercise targets are available. Open the full workout to review the remaining entries.", "attention")
    increases = sum(item.action in ("increase_reps", "increase_time", "equalize_weight", "increase_weight") for item in preview.recommendation.exercises)
    if increases:
        return OverviewConclusion("Your next progression targets are ready", f"The selected workout has {increases} exercise target(s) to increase. Follow the prescribed steps below.", "ready")
    return OverviewConclusion("Your next workout has clear targets", "Use the prescribed loads and ranges below. Another comparable log will inform the following decision.", "ready")
