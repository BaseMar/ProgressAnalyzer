"""Recurring prescription mismatches in the latest ordinary linked workout logs."""

from collections import defaultdict

from metrics.utils.dates import to_date

WINDOW_SIZE = 4
MINIMUM_ASSESSED = 3
MINIMUM_OCCURRENCES = 2
PATTERN_CODES = ("incomplete_sets", "below_range", "above_range", "below_target_rir")


def _position_identity(row):
    context = row["context"]
    identity = ("history", context[0]) if context[1:3] == (None, None) else ("legacy", *context[:4])
    return identity, row["planned_exercise_id"], row["actual_exercise_id"]


def _assess(row):
    """Use unknown rather than treating absent or excluded evidence as success."""
    result = dict.fromkeys(PATTERN_CODES)
    excluded = set(row["excluded_set_kinds"])
    if row["ambiguous_recorded_exercises"] or "invalid" in excluded:
        return result
    complete = not row["missing_sets"] and len(row["sets"]) == row["planned_sets"]
    if complete or not excluded.intersection(("light", "low_effort")):
        result["incomplete_sets"] = not complete
    for code in ("below_range", "above_range"):
        if row[code]:
            result[code] = True
        elif complete:
            result[code] = False
    if row["unit"] == "reps" and row["target_rir"] is not None:
        known = [item["rir"] for item in row["sets"] if item["rir"] is not None]
        if any(value < row["target_rir"] for value in known):
            result["below_target_rir"] = True
        elif complete and len(known) == row["planned_sets"]:
            result["below_target_rir"] = False
    return result


def summarize_recurring_deviations(performance, *, as_of, settings_by_version=None):
    """Assess up to four recent dates per position and actual exercise.

    Only linked ordinary workouts performed through as_of enter the window.
    Multiple same-day logs count once, retaining the latest input-order record.
    Changed prescriptions, positions or block settings start a new segment;
    identical plan revisions keep their history. Invalid or ambiguous records
    remain in the four-log window with unknown assessments, never replaced by
    older evidence. Unknown RIR does not prevent checking logged quantities.
    """
    settings = settings_by_version or {}
    groups = defaultdict(dict)
    for row in performance:
        if (
            row["session_id"] is None
            or row["performed_on"] is None
            or to_date(row["performed_on"]) > as_of
            or row["training_phase"] == "deload"
        ):
            continue
        groups[_position_identity(row)][to_date(row["performed_on"])] = row

    patterns = []
    assessed_contexts = pending_contexts = 0
    for by_date in groups.values():
        segment = []
        signature = None
        for day in sorted(by_date):
            row = by_date[day]
            current = (row["context"], settings.get(row["version_id"]))
            if current != signature:
                segment = []
                signature = current
            segment.append(row)
        recent = segment[-WINDOW_SIZE:]
        assessments = [(row, _assess(row)) for row in recent]
        enough_evidence = False
        for code in PATTERN_CODES:
            assessed = [
                (row, result[code]) for row, result in assessments if result[code] is not None
            ]
            if len(assessed) < MINIMUM_ASSESSED:
                continue
            enough_evidence = True
            affected = [row for row, mismatch in assessed if mismatch]
            if len(affected) < MINIMUM_OCCURRENCES:
                continue
            latest = recent[-1]
            patterns.append(
                {
                    "code": code,
                    "context": latest["context"],
                    "exercise_id": latest["actual_exercise_id"],
                    "workout": latest["workout"],
                    "position": latest["context"][3],
                    "planned_sets": latest["planned_sets"],
                    "target_min": latest["target_min"],
                    "target_max": latest["target_max"],
                    "target_rir": latest["target_rir"],
                    "unit": latest["unit"],
                    "occurrences": len(affected),
                    "assessed": len(assessed),
                    "window_size": len(recent),
                    "last_seen": to_date(affected[-1]["performed_on"]),
                    "evidence": tuple(
                        (row["session_id"], to_date(row["performed_on"]), result[code])
                        for row, result in assessments
                    ),
                }
            )
        if enough_evidence:
            assessed_contexts += 1
        else:
            pending_contexts += 1
    patterns.sort(
        key=lambda row: (
            -row["last_seen"].toordinal(),
            -row["occurrences"] / row["assessed"],
            row["workout"].casefold(),
            row["position"],
            row["exercise_id"],
            PATTERN_CODES.index(row["code"]),
        )
    )
    return {
        "patterns": patterns,
        "assessed_contexts": assessed_contexts,
        "pending_contexts": pending_contexts,
    }
