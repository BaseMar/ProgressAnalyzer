from data_manager import DataManager


def test_add_exercise_returns_insert_result(monkeypatch):
    manager = object.__new__(DataManager)
    manager.engine = object()

    monkeypatch.setattr("data_manager.insert_exercise", lambda *args: False)

    assert manager.add_exercise("New Exercise", "Push", "Chest") is False
