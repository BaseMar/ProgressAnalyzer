"""Deterministic synthetic workload; never reads or populates the application database."""
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Time, create_engine, event
from sqlalchemy.pool import StaticPool

from db.exercise_history_load_settings import confirm_legacy_body_mass_history
from db.migrate import migrate
from db.plan_adherence import save_exercise_match
from db.recorded_workouts import actual_exercises, actual_sets
from db.plan_schedule import assign_scheduled_session, load_scheduled_workouts
from db.set_classifications import classifications
from db.set_loads import insert_set_load
from db.training_plans import save_training_plan
from models.set_load import SetLoad
from models.training_plan import PlannedExercise, ProgressionSettings, TrainingDay, TrainingPlanDraft


AS_OF = date(2026, 11, 9)
FIXTURE_VERSION = 1
CATALOG = (
    (1, 'Barbell Bench Press', 'Chest'), (2, 'Cable Row', 'Back'),
    (3, 'Pull-Up', 'Back'), (4, 'Assisted Pull-Up', 'Back'),
    (5, 'Dead hang', 'Forearms'), (6, 'Dumbbell Curl', 'Biceps'),
    (7, 'Leg Press', 'Legs'), (8, 'Plank', 'Abs'),
    (9, 'Machine Chest Press', 'Chest'), (10, 'New Exercise', 'Shoulders'),
)
DAY_EXERCISES = (
    ('Upper A', (1, 2, 3, 6, 5, 8)), ('Lower A', (7, 2, 6, 1, 4, 8)),
    ('Upper B', (1, 2, 4, 6, 5, 8)), ('Lower B', (7, 2, 6, 1, 3, 8)),
    ('Arms', (6, 3, 4, 1, 2, 5)),
)


def create_fixture(weeks=24):
    if not 2 <= weeks <= 104:
        raise ValueError('Fixture weeks must be between 2 and 104')
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    metadata = MetaData()
    catalog = Table('exercises', metadata, Column('exercise_id', Integer, primary_key=True),
        Column('exercise_name', String), Column('category', String), Column('body_part', String))
    sessions = Table('workout_sessions', metadata, Column('session_id', Integer, primary_key=True),
        Column('session_date', Date), Column('start_time', Time), Column('end_time', Time), Column('notes', String))
    Table('workout_exercises', metadata, Column('workout_exercise_id', Integer, primary_key=True),
        Column('session_id', ForeignKey('workout_sessions.session_id')), Column('exercise_id', ForeignKey('exercises.exercise_id')))
    Table('workout_sets', metadata, Column('set_id', Integer, primary_key=True),
        Column('workout_exercise_id', ForeignKey('workout_exercises.workout_exercise_id')),
        Column('set_number', Integer), Column('repetitions', Integer), Column('weight', Float),
        Column('rir', Integer), Column('duration_seconds', Integer))
    muscle_map = Table('exercise_muscle_map', metadata, Column('exercise_id', Integer),
        Column('muscle_group', String), Column('muscle_name', String), Column('role', String),
        Column('set_factor', Float), Column('source_note', String))
    body = Table('body_composition', metadata, Column('measurement_date', DateTime),
        Column('weight', Float), Column('muscle_mass', Float), Column('fat_mass', Float),
        Column('water_mass', Float), Column('body_fat_percentage', Float), Column('method', String))
    measurements = Table('body_measurements', metadata, Column('measurement_date', DateTime),
        *(Column(name, Float) for name in ('chest', 'waist', 'abdomen', 'hips', 'thigh', 'calf', 'biceps')))
    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(catalog.insert(), [dict(exercise_id=eid, exercise_name=name, category='Synthetic', body_part=group)
            for eid, name, group in CATALOG])
        connection.execute(muscle_map.insert(), [dict(exercise_id=eid, muscle_group=group,
            muscle_name=group, role='primary', set_factor=1., source_note='Synthetic baseline') for eid, _, group in CATALOG])
    migrate(engine, apply=True)
    start = AS_OF - timedelta(weeks=weeks)

    def prescription(eid):
        timed = eid in (5, 8)
        return PlannedExercise(eid, 1 if timed else 3, 30 if timed else 6, 60 if timed else 10,
            target_unit='seconds' if timed else 'reps', target_rir=None if timed else 2, weight_increment=2.5)

    draft = TrainingPlanDraft('Synthetic baseline', start,
        tuple(TrainingDay(name, index, tuple(prescription(eid) for eid in ids))
              for index, (name, ids) in enumerate(DAY_EXERCISES)), ProgressionSettings(start, 7))
    original = save_training_plan(engine, draft)
    slots = load_scheduled_workouts(engine, original.plan_id, start, AS_OF - timedelta(days=1))
    base_weights = {1: (60., 55., 55.), 2: (70.,) * 3, 3: (80.,) * 3,
                    4: (0.,) * 3, 5: (0.,), 6: (12., 10., 10.), 7: (100.,) * 3, 8: (0.,)}
    for sid, slot in enumerate(slots, 1):
        replacements = []
        with engine.begin() as connection:
            connection.execute(sessions.insert().values(session_id=sid, session_date=slot.scheduled_date,
                start_time=time(15), end_time=time(16), notes='Synthetic baseline'))
            ids = DAY_EXERCISES[slot.position - 1][1]
            for position, eid in enumerate(ids, 1):
                actual_id = 9 if slot.scheduled_date == AS_OF - timedelta(days=7) and eid == 1 else eid
                weid = sid * 100 + position
                connection.execute(actual_exercises.insert().values(workout_exercise_id=weid, session_id=sid, exercise_id=actual_id))
                if actual_id != eid:
                    replacements.append((position - 1, weid))
                if position == 1 and eid not in (3, 4, 5, 8):
                    set_id = connection.execute(actual_sets.insert().values(workout_exercise_id=weid,
                        set_number=1, repetitions=10, weight=20., rir=5)).inserted_primary_key[0]
                    connection.execute(classifications.insert().values(set_id=set_id, is_warmup=True))
                for index, weight in enumerate(base_weights[eid], 2):
                    rir = None if eid in (5, 8) or (eid == 6 and slot.scheduled_date >= AS_OF - timedelta(days=7)) else 2
                    set_id = connection.execute(actual_sets.insert().values(workout_exercise_id=weid,
                        set_number=index, repetitions=0 if eid in (5, 8) else 10 if eid in (1, 6, 7) else 8,
                        weight=weight, rir=rir, duration_seconds=35 if eid in (5, 8) else None)).inserted_primary_key[0]
                    connection.execute(classifications.insert().values(set_id=set_id, is_warmup=False))
                    if eid == 4:
                        insert_set_load(connection, set_id, SetLoad('assisted_bodyweight', 0., 80., 20.))
        assign_scheduled_session(engine, slot.day_id, slot.scheduled_date, sid)
        if replacements:
            from db.plan_adherence import load_plan_adherence
            targets = load_plan_adherence(engine, original.plan_id, slot.scheduled_date, slot.scheduled_date).workouts[0].targets
            for position, weid in replacements:
                save_exercise_match(engine, sid, targets[position].plan_exercise_id, weid)
    with engine.begin() as connection:
        for week in range(weeks):
            stamp = datetime.combine(start + timedelta(weeks=week), time.min)
            connection.execute(body.insert().values(measurement_date=stamp, weight=80. + week * .1,
                muscle_mass=35. + week * .02, fat_mass=15., water_mass=45., body_fat_percentage=18., method='Synthetic'))
            connection.execute(measurements.insert().values(measurement_date=stamp, chest=100. + week * .1,
                waist=80., abdomen=82., hips=95., thigh=55., calf=36., biceps=34.))
        for sid, day, weight in ((len(slots) + 1, AS_OF - timedelta(days=2), 62.5),
                                 (len(slots) + 2, AS_OF + timedelta(days=1), 200.)):
            connection.execute(sessions.insert().values(session_id=sid, session_date=day, notes='Unlinked synthetic entry'))
            connection.execute(actual_exercises.insert().values(workout_exercise_id=sid * 100, session_id=sid, exercise_id=1))
            connection.execute(actual_sets.insert(), [dict(workout_exercise_id=sid * 100, set_number=n,
                repetitions=8, weight=weight, rir=2) for n in (1, 2, 3)])
    revised_days = tuple(replace(day, exercises=tuple(
        replace(item, target_rir=3) if item.exercise_id == 1 else
        replace(item, set_count=4) if item.exercise_id == 2 else item for item in day.exercises))
        for day in original.draft.days)
    with patch('db.training_plans.date') as clock:
        clock.today.return_value = AS_OF
        revised = save_training_plan(engine, replace(original.draft, effective_from=AS_OF, days=revised_days), plan_id=original.plan_id)
    confirm_legacy_body_mass_history(engine, 3)
    return engine, revised
