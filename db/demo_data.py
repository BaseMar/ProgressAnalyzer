"""Generate a fictional training history from constants, never from user records."""

from dataclasses import asdict
from datetime import datetime, time, timedelta

from db.exercise_muscle_resolver import resolve_exercise
from db.plan_adherence import load_plan_adherence, save_exercise_match
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.set_classifications import classifications
from db.set_loads import insert_set_load
from db.training_plans import save_training_plan
from models.set_load import SetLoad
from models.training_plan import (
    PlannedExercise,
    ProgressionSettings,
    TrainingDay,
    TrainingPlanDraft,
)

CATALOG = (
    "Barbell Bench Press",
    "Cable Row",
    "Dumbbell Curl",
    "Leg Press",
    "Pull-Up",
    "Assisted Pull-Up",
    "Plank",
    "Machine Chest Press",
    "Dead hang",
)
ROUTINE = (
    ("Upper", 0, ("Barbell Bench Press", "Cable Row", "Pull-Up", "Dumbbell Curl", "Plank")),
    ("Lower", 2, ("Leg Press", "Cable Row", "Assisted Pull-Up", "Dumbbell Curl", "Plank")),
    ("Full body", 4, ("Barbell Bench Press", "Leg Press", "Pull-Up", "Dead hang", "Plank")),
)
BASE_LOADS = {
    "Barbell Bench Press": 60.0,
    "Cable Row": 50.0,
    "Dumbbell Curl": 10.0,
    "Leg Press": 100.0,
    "Machine Chest Press": 45.0,
}


def _prescription(name, exercise_id):
    if name in ("Plank", "Dead hang"):
        return PlannedExercise(exercise_id, 2, 20, 60, "seconds", None, None)
    return PlannedExercise(exercise_id, 3, 8, 12, "reps", 2, 2.5)


def _catalog(connection, tables):
    ids = {}
    for name in CATALOG:
        resolution = resolve_exercise(name, allow_web=False)
        if resolution is None:
            raise ValueError(f"Missing offline demo mapping: {name}")
        exercise_id = connection.execute(
            tables["exercises"]
            .insert()
            .values(
                exercise_name=name,
                category=resolution.category,
                body_part=resolution.body_part,
            )
        ).inserted_primary_key[0]
        ids[name] = exercise_id
        connection.execute(
            tables["exercise_muscle_map"].insert(),
            [dict(exercise_id=exercise_id, **asdict(target)) for target in resolution.targets],
        )
    return ids


def _record(
    connection,
    tables,
    session_id,
    exercise_id,
    name,
    week,
    body_mass,
    *,
    deload=False,
    warmup=False,
):
    entry_id = connection.execute(
        tables["workout_exercises"]
        .insert()
        .values(
            session_id=session_id,
            exercise_id=exercise_id,
        )
    ).inserted_primary_key[0]
    timed = name in ("Plank", "Dead hang")
    bodyweight = name in ("Pull-Up", "Assisted Pull-Up", "Dead hang")
    kind = (
        "assisted_bodyweight"
        if name == "Assisted Pull-Up"
        else "bodyweight"
        if bodyweight
        else "external"
    )
    base = BASE_LOADS.get(name, 0.0) + (2.5 * (week // 3) if name in BASE_LOADS else 0)
    count = 2 if timed else 3
    for index in range(count + int(warmup)):
        preparation = warmup and index == 0
        working_index = index - int(warmup)
        weight = base
        if name == "Barbell Bench Press" and working_index > 0:
            weight -= 5
        if deload:
            weight = round(weight * 0.65 / 2.5) * 2.5
        if preparation:
            weight = round(base * 0.5 / 2.5) * 2.5
        duration = (30 if deload else 35 + 5 * (week % 3)) if timed else None
        rir = None if timed else 5 if preparation else 4 if deload else 2
        if name == "Dumbbell Curl" and week == 8 and working_index == count - 1:
            rir = None
        set_id = connection.execute(
            tables["workout_sets"]
            .insert()
            .values(
                workout_exercise_id=entry_id,
                set_number=index + 1,
                repetitions=0 if timed else 10 if preparation else 10 + week % 3,
                weight=weight,
                duration_seconds=duration,
                rir=rir,
            )
        ).inserted_primary_key[0]
        connection.execute(
            classifications.insert().values(set_id=set_id, is_warmup=bool(preparation))
        )
        insert_set_load(
            connection,
            set_id,
            SetLoad(
                kind,
                weight,
                body_mass if bodyweight else None,
                (25.0 if deload else 15.0) if kind == "assisted_bodyweight" else 0.0,
            ),
        )
    return entry_id


def seed_demo(scope, tables, *, as_of):
    """Populate only the newly created schema, within the caller's transaction."""
    connection = scope.connection
    ids = _catalog(connection, tables)
    start = as_of - timedelta(days=as_of.weekday(), weeks=8)
    draft = TrainingPlanDraft(
        "Demo full-body plan",
        start,
        tuple(
            TrainingDay(name, weekday, tuple(_prescription(ex, ids[ex]) for ex in exercises))
            for name, weekday, exercises in ROUTINE
        ),
        ProgressionSettings(start, 6),
    )
    plan = save_training_plan(scope, draft)
    slots = load_scheduled_workouts(scope, plan.plan_id, start, as_of - timedelta(days=1))
    for slot in slots:
        week = (slot.scheduled_date - start).days // 7
        moved = week == 6 and slot.position == 1
        performed = slot.scheduled_date + timedelta(days=int(moved))
        session_id = connection.execute(
            tables["workout_sessions"]
            .insert()
            .values(
                session_date=performed,
                start_time=time(17, 0),
                end_time=time(18, 0),
                notes="Fictional demo workout" + ("; moved one day" if moved else ""),
            )
        ).inserted_primary_key[0]
        replacement = None
        for position, planned_name in enumerate(ROUTINE[slot.position - 1][2]):
            name = "Machine Chest Press" if moved and position == 0 else planned_name
            entry_id = _record(
                connection,
                tables,
                session_id,
                ids[name],
                name,
                week,
                78.0 - 0.15 * week,
                deload=week % 6 == 5,
                warmup=position == 0 and name in BASE_LOADS,
            )
            if name != planned_name:
                replacement = entry_id
        assign_scheduled_session(scope, slot.day_id, slot.scheduled_date, session_id)
        if replacement is not None:
            history = load_plan_adherence(
                scope, plan.plan_id, slot.scheduled_date, slot.scheduled_date
            )
            target_id = history.workouts[0].targets[0].plan_exercise_id
            save_exercise_match(scope, session_id, target_id, replacement)
    # Unlinked practice illustrates the difference between raw history and plan coverage.
    session_id = connection.execute(
        tables["workout_sessions"]
        .insert()
        .values(
            session_date=start + timedelta(days=16),
            notes="Fictional unlinked practice",
        )
    ).inserted_primary_key[0]
    _record(
        connection, tables, session_id, ids["Machine Chest Press"], "Machine Chest Press", 2, 77.7
    )
    for week in range(9):
        measured = datetime.combine(start + timedelta(weeks=week), time())
        weight = round(78.0 - week * 0.15, 2)
        connection.execute(
            tables["body_composition"]
            .insert()
            .values(
                measurement_date=measured,
                weight=weight,
                muscle_mass=34.0 + week * 0.05,
                fat_mass=15.0 - week * 0.1,
                water_mass=45.0,
                body_fat_percentage=round((15.0 - week * 0.1) / weight * 100, 2),
                method="Synthetic demo values",
            )
        )
        connection.execute(
            tables["body_measurements"]
            .insert()
            .values(
                measurement_date=measured,
                chest=100.0 + week * 0.1,
                waist=86.0 - week * 0.2,
                abdomen=89.0 - week * 0.2,
                hips=97.0,
                thigh=57.0,
                calf=37.0,
                biceps=33.0 + week * 0.05,
            )
        )
