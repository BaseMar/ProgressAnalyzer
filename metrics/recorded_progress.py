"""Describe the latest recorded exercise results independently of any plan.

The window selects latest results, not their preceding evidence. Plan links,
prescriptions, revisions and recommendation history gaps do not gate progress.
Actual load, reserve, set purpose and units still determine comparability.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import time
from math import isclose, isfinite

from metrics.load_metrics import describe_load, load_comparison_problem, load_record, same_loads
from metrics.set_interpretation import interpret_sets
from metrics.utils.dates import to_date
from models.training_insights import (
    ExerciseProgressSummary,
    InsightReport,
    InsightSet,
    InsightSource,
    TrainingInsight,
)


@dataclass(frozen=True)
class _Execution:
    exercise_id: int
    source: InsightSource
    unit: str
    problem: str | None


def _positive(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
    )


def _session_order(session):
    started = session.start_time
    if isinstance(started, str):
        started = time.fromisoformat(started)
    return to_date(session.session_date), started or time.min, session.session_id


def _execution(session, exercises, sets_by_exercise, deload_ids):
    """Keep incomplete/latest logs visible; never silently reuse an older success."""
    exercise_id = exercises[0].exercise_id
    raw = sorted(
        (item for exercise in exercises for item in sets_by_exercise[exercise.workout_exercise_id]),
        key=lambda item: item.set_number,
    )
    interpreted = interpret_sets(raw, deload_exercise_ids=deload_ids)
    retained, units, excluded = [], set(), set()
    problem = None
    for item, meaning in zip(raw, interpreted):
        if meaning.kind in ("warmup", "light", "low_effort"):
            excluded.add(meaning.kind)
            continue
        timed = _positive(item.duration_seconds)
        quantity = item.duration_seconds if timed else item.repetitions
        units.add("seconds" if timed else "reps")
        if meaning.kind == "invalid" or not _positive(quantity):
            problem = "invalid recorded values"
        elif meaning.kind == "deload":
            problem = "deload work"
        elif not timed and item.rir is None:
            problem = "missing RIR (repetitions in reserve)"
        retained.append(
            InsightSet(
                quantity,
                item.weight,
                item.rir,
                meaning.kind,
                meaning.source,
                meaning.reason,
                **load_record(item),
                unit="seconds" if timed else "reps",
            )
        )
    if len(exercises) != 1:
        problem = "multiple entries for the exercise in one session"
    elif len({item.set_number for item in raw}) != len(raw):
        problem = "duplicate set numbers"
    elif len(units) > 1:
        problem = "mixed repetitions and seconds"
    elif not retained:
        problem = "no recorded working sets"
    if any(exercise.workout_exercise_id in deload_ids for exercise in exercises):
        problem = "deload work"
    source = InsightSource(
        session.session_id,
        None,
        to_date(session.session_date),
        "Recorded workout",
        (exercise_id,),
        "deload" if problem == "deload work" else "recorded",
        None,
        None,
        None,
        None,
        tuple(retained),
        tuple(sorted(excluded)),
    )
    return _Execution(exercise_id, source, next(iter(units), "reps"), problem)


def _loads(execution):
    return [vars(item) for item in execution.source.sets]


def _result(execution):
    source = execution.source
    quantities = "/".join(f"{item.quantity:g}" for item in source.sets)
    loads = " / ".join(dict.fromkeys(describe_load(item) for item in _loads(execution)))
    reserve = "/".join("?" if item.rir is None else f"{item.rir:g}" for item in source.sets)
    return f"{source.performed_on:%d %b %Y}: {quantities} {execution.unit} @ {loads}" + (
        f" · RIR {reserve}" if execution.unit == "reps" else ""
    )


def _pair_problem(previous, current):
    if current.problem:
        return current.problem
    if previous is None:
        return "first recorded result"
    if previous.problem:
        return f"previous result: {previous.problem}"
    if previous.source.performed_on == current.source.performed_on:
        return "two sessions on the same day"
    if previous.unit != current.unit:
        return "repetitions and seconds cannot be compared"
    if len(previous.source.sets) != len(current.source.sets):
        return "working set count changed"
    problem = load_comparison_problem(_loads(current), _loads(previous))
    if problem:
        return {
            "unknown_load": "unknown body mass or assistance",
            "load_convention_changed": "load convention changed",
        }[problem]
    return None


def _comparison(previous, current):
    changed_load = not same_loads(_loads(current), _loads(previous))
    changed_rir = current.unit == "reps" and any(
        now.rir != old.rir for now, old in zip(current.source.sets, previous.source.sets)
    )
    delta = sum(item.quantity for item in current.source.sets) - sum(
        item.quantity for item in previous.source.sets
    )
    suffix = " and RIR" if current.unit == "reps" else ""
    if changed_load:
        code, priority = "load_changed", 40
        observation = "Load changed — compare it alongside reps or time"
        action = "Open Analysis to review the load and output together."
    elif changed_rir:
        code, priority = "effort_changed", 30
        observation = "Recorded reserve changed — output needs context"
        action = "RIR means repetitions in reserve. Compare results at the same recorded reserve."
    elif isclose(delta, 0, rel_tol=0, abs_tol=1e-6):
        code, priority = "same_output", 50
        observation = f"Same total output at the same load{suffix}"
        action = "Use Next workout for the next target; equal output alone is not a plateau."
    elif delta > 0:
        code, priority = "more_output", 20
        observation = f"{delta:g} more {current.unit} at the same load{suffix}"
        action = "Use Next workout to decide the next target."
    else:
        code, priority = "less_output", 25
        observation = f"{-delta:g} fewer {current.unit} at the same load{suffix}"
        action = "Check the next comparable result before drawing conclusions from one workout."
    return TrainingInsight(
        code,
        priority,
        observation,
        f"{_result(previous)} → {_result(current)}",
        action,
        "paired",
        "Latest two recorded sessions of the same catalog exercise, independent of plan or linkage. "
        "Equal working set counts and units; per-set load conventions, total loads and actual RIR "
        "must match for an output verdict. Changed loads or reserve do not establish improvement. "
        "This describes logged output, not technique, muscle growth or fatigue.",
        (previous.source, current.source),
        current.exercise_id,
    )


def _recorded_histories(data, *, cutoff, exercise_id=None):
    exercises_by_session = defaultdict(lambda: defaultdict(list))
    sets_by_exercise = defaultdict(list)
    for exercise in data.workout_exercises:
        if exercise_id is not None and exercise.exercise_id != exercise_id:
            continue
        exercises_by_session[exercise.session_id][exercise.exercise_id].append(exercise)
    for item in data.sets:
        sets_by_exercise[item.workout_exercise_id].append(item)
    histories = defaultdict(list)
    for session in sorted(data.sessions, key=_session_order):
        if to_date(session.session_date) > cutoff:
            continue
        for catalog_id, exercises in exercises_by_session[session.session_id].items():
            histories[catalog_id].append(
                _execution(session, exercises, sets_by_exercise, data.deload_exercise_ids)
            )
    return histories


def compare_recorded_exercise(data, exercise_id, *, as_of, start=None, end=None):
    """Expose the latest pair and its evidence using Overview's comparison rules.

    The latest execution must be inside the selected period. Its immediate
    predecessor may be older. Never filter out an incomplete log, changed load
    convention, or deload to find a more favorable pair.
    """
    cutoff = min(as_of, end) if end is not None else as_of
    history = _recorded_histories(data, cutoff=cutoff, exercise_id=exercise_id).get(exercise_id)
    if not history or (start is not None and history[-1].source.performed_on < start):
        return None
    current = history[-1]
    previous = history[-2] if len(history) > 1 else None
    problem = _pair_problem(previous, current)
    if problem is None:
        return _comparison(previous, current)
    return TrainingInsight(
        "limited_evidence",
        35,
        "No comparable change available",
        problem[0].upper() + problem[1:] + ".",
        "Review the source sessions in History. The latest recorded execution remains the comparison baseline.",
        "limited",
        "Same latest-pair rules as Overview; incomplete or ineligible executions are never skipped.",
        tuple(item.source for item in (previous, current) if item is not None),
        exercise_id,
    )


def compute_recorded_progress(data, *, as_of, start=None, end=None):
    """Count each exercise once, using its latest result within the actual-date window.

    Compare with its immediate previous recorded session, including older or
    unlinked history. Incomplete results and deloads are barriers, not skipped
    records. A long gap is shown in the evidence dates, never hidden by a plan
    recommendation cutoff. Annotation limits cannot bias counts or highlights.
    """
    cutoff = min(as_of, end) if end is not None else as_of
    histories = _recorded_histories(data, cutoff=cutoff)
    annotations, limitations = [], []
    statuses = Counter()
    for history in histories.values():
        current = history[-1]
        if start is not None and current.source.performed_on < start:
            continue
        previous = history[-2] if len(history) > 1 else None
        problem = _pair_problem(previous, current)
        if problem:
            statuses["unassessed"] += 1
            limitations.append((problem, current.source))
            continue
        insight = _comparison(previous, current)
        annotations.append(insight)
        statuses[
            {"more_output": "improving", "less_output": "lower", "same_output": "unchanged"}.get(
                insight.code, "unassessed"
            )
        ] += 1

    def relative_change(insight):
        previous, current = insight.sources
        baseline = sum(item.quantity for item in previous.sets)
        delta = sum(item.quantity for item in current.sets) - baseline
        return abs(delta / baseline), current.performed_on, -insight.exercise_id

    highlights = tuple(
        selected
        for code in ("more_output", "less_output")
        if (
            selected := max(
                (item for item in annotations if item.code == code),
                key=relative_change,
                default=None,
            )
        )
        is not None
    )
    if limitations:
        reasons = Counter(reason for reason, _ in limitations)
        annotations.append(
            TrainingInsight(
                "limited_evidence",
                35,
                "Some exercises cannot be compared yet",
                "; ".join(f"{count} × {reason}" for reason, count in sorted(reasons.items())) + ".",
                "Check the recorded sets in History. A first result needs another workout; no plan link is required.",
                "limited",
                "Never substitute an older positive result for an incomplete latest log.",
                tuple(source for _, source in limitations),
            )
        )
    annotations.sort(
        key=lambda item: (
            item.priority,
            -max(source.performed_on.toordinal() for source in item.sources),
            item.exercise_id or 0,
        )
    )
    counts = ExerciseProgressSummary(
        **{name: statuses[name] for name in ("improving", "unchanged", "lower", "unassessed")}
    )
    return InsightReport(
        tuple(annotations[:5]),
        counts.compared,
        counts.unassessed,
        max(0, len(annotations) - 5),
        counts,
        highlights,
    )
