"""Short decisions derived from logged facts and the existing target engine.

The date window selects scheduled dates by default; Overview selects actual
dates. Actual dates and session_order determine comparisons. Earlier history remains available. These
are application rules, not estimates of muscle growth or training quality.
"""

from collections import Counter, defaultdict
from datetime import date

from metrics.load_metrics import describe_load, load_comparison_problem, recorded_load, same_loads
from metrics.plan_performance import comparison_context, compute_plan_performance
from metrics.utils.recommendation_text import goal_summary
from models.training_insights import (
    ExerciseProgressSummary,
    InsightPolicy,
    InsightReport,
    InsightSet,
    InsightSource,
    TrainingInsight,
)


def _source(row):
    field = "seconds" if row["unit"] == "seconds" else "reps"
    return InsightSource(
        row["session_id"],
        row["scheduled_date"],
        row["performed_on"],
        row["workout"],
        row["context"],
        row["training_phase"],
        row["planned_sets"],
        row["target_min"],
        row["target_max"],
        row["target_rir"],
        tuple(
            InsightSet(
                item[field],
                item["weight"],
                item["rir"],
                item["set_kind"],
                item["classification_source"],
                item["classification_reason"],
                item.get("load_type", "legacy"),
                recorded_load(item),
                item.get("body_mass_kg"),
                item.get("assistance_kg"),
                unit=row["unit"],
            )
            for item in row["sets"]
        ),
        tuple(row["excluded_set_kinds"]),
    )


def _result(row):
    """Per-set vectors avoid disguising mixed loads or RIR with a mean."""
    field = "seconds" if row["unit"] == "seconds" else "reps"
    quantities = "/".join(f"{item[field]:g}" for item in row["sets"])
    load = " / ".join(dict.fromkeys(describe_load(item) for item in row["sets"]))
    reserve = "/".join("?" if item["rir"] is None else str(item["rir"]) for item in row["sets"])
    return f"{row['performed_on']:%d %b}: {quantities} {row['unit']} @ {load}" + (
        f" · RIR {reserve}" if field == "reps" else ""
    )


def _limitation(row):
    if row.get("ambiguous_recorded_exercises"):
        return "ambiguous recorded exercise match"
    if not row["sets"]:
        kinds = set(row["excluded_set_kinds"])
        if kinds & {"light", "low_effort"}:
            return "only light/low-effort work"
        if "invalid" in kinds:
            return "invalid source values"
        return "no matching working sets"
    if row["missing_sets"]:
        return "incomplete set count"
    if any(recorded_load(item) is None for item in row["sets"]):
        return "unknown body mass or assistance"
    if row["unit"] == "reps" and row["rir_known_sets"] < len(row["sets"]):
        return "missing RIR"
    if not row["progression_eligible"]:
        return "insufficient ordinary effort evidence"
    return None


def _next_target(row, preview, *, as_of, end, settings_by_version):
    """Reuse a real preview only when it actually cites this observation."""
    if preview is None or (end is not None and end < as_of):
        return None
    slot = preview.upcoming.slot
    if slot.scheduled_date < as_of or slot.scheduled_date <= row["performed_on"]:
        return None
    if settings_by_version.get(slot.version_id) != settings_by_version.get(row["version_id"]):
        return None
    for position, (target, recommendation) in enumerate(
        zip(preview.upcoming.targets, preview.recommendation.exercises), 1
    ):
        if (
            recommendation.action == "insufficient_data"
            or not recommendation.goals
            or row["session_id"] not in recommendation.evidence_session_ids
            or recommendation.plan_exercise_id != target.plan_exercise_id
        ):
            continue
        context = comparison_context(
            slot, position, target.exercise, recommendation.actual_exercise_id
        )
        if context == row["context"] and recommendation.scheduled_date == slot.scheduled_date:
            return recommendation
    return None


def compute_training_insights(
    data,
    *,
    as_of: date,
    start=None,
    end=None,
    settings_by_version=None,
    preview=None,
    policy=InsightPolicy(),
    date_basis="scheduled",
):
    """Return prioritized annotations and uncapped exercise progress counts with immutable evidence.

    Select the latest *linked* execution per context, including an empty or
    incomplete one. Never fall back to an older success. Substitutes and changed
    prescriptions remain separate; a manual block reset starts a new history.
    Unlinked elapsed slots describe missing linkage, never skipped workouts.
    """
    if date_basis not in ("scheduled", "performed"):
        raise ValueError("Date basis must be scheduled or performed")
    settings = settings_by_version or {}
    rows = compute_plan_performance(data, as_of=as_of, settings_by_version=settings)

    def inside(row):
        selected_date = (
            (row["performed_on"] or row["scheduled_date"])
            if date_basis == "performed"
            else row["scheduled_date"]
        )
        return (start is None or selected_date >= start) and (end is None or selected_date <= end)

    groups = defaultdict(list)
    unlinked = {}
    latest_by_exercise = {}
    for row in rows:
        if row["session_id"] is None:
            if inside(row) and row["scheduled_date"] < as_of:
                unlinked.setdefault((row["day_id"], row["scheduled_date"]), row)
            continue
        if row["performed_on"] is None or row["performed_on"] > as_of:
            continue
        groups[(row["context"], settings.get(row["version_id"]))].append(row)
        if inside(row):
            latest_by_exercise[row["actual_exercise_id"]] = row

    # Rows are in actual-session order. Count each catalog exercise once using
    # its latest result, even when that result is incomplete or in a new context.
    # The annotation limit must never limit or bias these counts.
    exercise_status = dict.fromkeys(latest_by_exercise, "unassessed")
    annotations, limitations, deloads = [], [], []
    highlight_candidates = []
    assessed = 0
    for history in groups.values():
        visible = [index for index, row in enumerate(history) if inside(row)]
        if not visible:
            continue
        index = visible[-1]
        current = history[index]
        if current["training_phase"] == "deload":
            deloads.append(current)
            continue
        problem = _limitation(current)
        if problem:
            limitations.append((problem, (current,)))
            continue
        target_rir = current["target_rir"]
        lower_reserve = (
            current["unit"] == "reps"
            and target_rir is not None
            and any(item["rir"] < target_rir for item in current["sets"])
        )
        if lower_reserve:
            recommendation = _next_target(
                current, preview, as_of=as_of, end=end, settings_by_version=settings
            )
            next_target = (
                f"{recommendation.scheduled_date:%d %b}: {goal_summary(recommendation)}"
                if recommendation
                else None
            )
            annotations.append(
                TrainingInsight(
                    "below_target_rir",
                    10,
                    "Less reserve than planned",
                    f"{current['workout']} · {_result(current)} · planned RIR ≥ {target_rir}.",
                    "Next target: " + next_target + "."
                    if next_target
                    else f"Aim for RIR ≥ {target_rir}. A failure at the minimum needs a set-specific correction; use the Next workout target.",
                    "observed",
                    "At least one current eligible set has less reserve than prescribed. This is an observed target mismatch, not a fatigue diagnosis.",
                    (_source(current),),
                    current["actual_exercise_id"],
                    next_target,
                    recommendation,
                )
            )
            continue
        previous = next(
            (row for row in reversed(history[:index]) if row["training_phase"] != "deload"), None
        )
        if previous is None:
            limitations.append(("first comparable execution", (current,)))
            continue
        problem = _limitation(previous)
        if problem:
            limitations.append((f"previous execution: {problem}", (previous, current)))
            continue
        if load_comparison_problem(current["sets"], previous["sets"]) is not None:
            limitations.append(("load convention changed", (previous, current)))
            continue
        gap = (current["performed_on"] - previous["performed_on"]).days
        if gap == 0:
            limitations.append(("executions on the same day", (previous, current)))
            continue
        if gap > policy.max_gap_days:
            limitations.append((f"gap over {policy.max_gap_days} days", (previous, current)))
            continue

        assessed += 1
        same_load = same_loads(current["sets"], previous["sets"])
        field = "seconds" if current["unit"] == "seconds" else "reps"
        delta = sum(item[field] for item in current["sets"]) - sum(
            item[field] for item in previous["sets"]
        )
        rir_pairs = [
            (now["rir"], old["rir"]) for now, old in zip(current["sets"], previous["sets"])
        ]
        effort_changed = field == "reps" and any(now != old for now, old in rir_pairs)
        rule = (
            f"Same exercise/context, complete eligible sets, different recorded days, gap ≤ {policy.max_gap_days} days. "
            "Compare per-set loads and RIR; totals describe logged output only."
        )
        if not same_load:
            code, priority = "load_changed", 40
            observation = "Load changed — read reps alongside it"
            action = "Use this load as the new reference; follow the Next workout target before increasing again."
            rule += " Changed load alone does not establish progress or regression."
        elif effort_changed:
            code, priority = "effort_changed", 30
            observation = "Effort changed — output needs context"
            action = "Repeat with the planned reserve to make the next result easier to compare."
            rule += " At least one set changed RIR; an average would hide this difference."
        elif delta > 0:
            code, priority = "more_output", 20
            observation = f"{delta:g} more {current['unit']} at the same load" + (
                " and RIR" if field == "reps" else ""
            )
            action = (
                "Follow the Next workout target; do not add an extra weight increase on top of it."
            )
            rule += (
                " Total output increased; per-set load and, for reps, recorded RIR are unchanged."
            )
        elif delta < 0:
            code, priority = "less_output", 25
            observation = f"{-delta:g} fewer {current['unit']} at the same load" + (
                " and RIR" if field == "reps" else ""
            )
            action = "Repeat the prescribed load and range; check the next comparable result before drawing conclusions."
            rule += " Lower logged output does not diagnose regression or fatigue."
        else:
            code, priority = "same_output", 50
            observation = "Same total output at the same load" + (
                " and RIR" if field == "reps" else ""
            )
            action = "Follow the Next workout target to decide between one more rep, a confirmed load increase or holding."
            rule += " Equal totals are an observation, not a plateau diagnosis."
        if latest_by_exercise.get(current["actual_exercise_id"]) is current:
            exercise_status[current["actual_exercise_id"]] = {
                "more_output": "improving",
                "same_output": "unchanged",
                "less_output": "lower",
            }.get(code, "unassessed")
        recommendation = _next_target(
            current, preview, as_of=as_of, end=end, settings_by_version=settings
        )
        next_target = (
            f"{recommendation.scheduled_date:%d %b}: {goal_summary(recommendation)}"
            if recommendation
            else None
        )
        if next_target:
            action = "Next target: " + next_target + "."
        annotations.append(
            TrainingInsight(
                code,
                priority,
                observation,
                f"{current['workout']} · {_result(previous)} → {_result(current)}",
                action,
                "paired",
                rule,
                (_source(previous), _source(current)),
                current["actual_exercise_id"],
                next_target,
                recommendation,
            )
        )

        if latest_by_exercise.get(current["actual_exercise_id"]) is current and code in (
            "more_output",
            "less_output",
        ):
            highlight_candidates.append(annotations[-1])

    def relative_change(insight):
        previous, current = insight.sources
        baseline = sum(item.quantity for item in previous.sets)
        change = sum(item.quantity for item in current.sets) - baseline
        return (
            abs(change / baseline) if baseline > 0 else 0,
            current.performed_on,
            -(insight.exercise_id or 0),
        )

    highlights = tuple(
        chosen
        for code in ("more_output", "less_output")
        if (
            chosen := max(
                (item for item in highlight_candidates if item.code == code),
                key=relative_change,
                default=None,
            )
        )
        is not None
    )

    if deloads:
        annotations.append(
            TrainingInsight(
                "deload",
                15,
                "Lighter work belongs to the planned deload",
                f"{len(deloads)} exercise contexts last recorded in deload; targets use the reduced prescription.",
                "Follow the block's deload target; resume ordinary loads after the lighter week.",
                "observed",
                "Scheduled or actual deload phase uses reduced targets. These logs are excluded from ordinary progress comparisons.",
                tuple(_source(row) for row in deloads),
            )
        )
    if limitations or unlinked:
        reasons = Counter(reason for reason, _ in limitations)
        details = "; ".join(f"{count} × {reason}" for reason, count in sorted(reasons.items()))
        if unlinked:
            details += (
                "; " if details else ""
            ) + f"{len(unlinked)} elapsed planned workouts without linked logs"
        sources = tuple(
            dict.fromkeys(_source(row) for _, entries in limitations for row in entries)
        )
        sources += tuple(_source(row) for row in unlinked.values())
        annotations.append(
            TrainingInsight(
                "limited_evidence",
                35,
                "Some results need more evidence",
                details + ".",
                "Complete the source RIR/set data or link the recorded session. For a first result or long gap, log another comparable workout.",
                "limited",
                f"No verdict for missing/incomplete effort evidence, first execution, same-day pairs or gaps over {policy.max_gap_days} days. "
                "Missing linkage is not proof of skipped training; never reuse an older success over an incomplete latest log.",
                sources,
            )
        )
    annotations.sort(
        key=lambda item: (
            item.priority,
            -(
                max(
                    (source.performed_on or source.scheduled_date).toordinal()
                    for source in item.sources
                )
            ),
            item.exercise_id or 0,
            item.code,
        )
    )
    return InsightReport(
        tuple(annotations[: policy.max_annotations]),
        assessed,
        len(limitations),
        max(0, len(annotations) - policy.max_annotations),
        ExerciseProgressSummary(
            **{
                name: sum(value == name for value in exercise_status.values())
                for name in ("improving", "unchanged", "lower", "unassessed")
            }
        ),
        highlights,
    )
