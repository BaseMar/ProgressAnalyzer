"""Exercise the active storage-to-domain path on an isolated workload."""
from datetime import time, timedelta
from data_manager import DataManager
from metrics.utils.dates import to_date
from scripts.baseline_fixture import AS_OF, create_fixture
from scripts.baseline_snapshot import load_input


def test_active_loader_maps_sessions_body_columns_targets_and_load_snapshots():
    engine, _ = create_fixture(weeks=2)
    try:
        data, displayed_sets = load_input(engine)
        assert len(data.sessions) == 12 and len(data.sets) == len(displayed_sets)
        assert len(data.exercises) == len(data.exercise_muscle_targets) == 10
        first = min(data.sessions, key=lambda session: session.session_date)
        assert to_date(first.session_date) == AS_OF - timedelta(weeks=2)
        assert time.fromisoformat(str(first.start_time)) == time(15)
        assert time.fromisoformat(str(first.end_time)) == time(16)
        assert len(data.body_composition) == 2
        assert len(data.body_measurements) == 14
        assert {item.measurement_type for item in data.body_measurements} == {
            'chest', 'waist', 'abdomen', 'hips', 'thigh', 'calf', 'biceps',
        }
        assert any(item.is_warmup is True for item in data.sets)
        assert any(item.duration_seconds == 35 and item.rir is None for item in data.sets)
        assisted = next(item for item in data.sets if item.load is not None)
        assert assisted.load.load_type == 'assisted_bodyweight'
        assert assisted.load.body_mass_kg == 80. and assisted.load.assistance_kg == 20.
        manager = DataManager(engine=engine)
        assert len(manager.load_workout_exercises()) == len(data.workout_exercises)
    finally:
        engine.dispose()
