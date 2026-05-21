from db.queries import insert_exercise


class _Connection:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((str(query), params))


class _BeginContext:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _Engine:
    def __init__(self):
        self.conn = _Connection()

    def begin(self):
        return _BeginContext(self.conn)


def test_insert_exercise_assigns_next_exercise_id():
    engine = _Engine()

    assert insert_exercise(engine, "Incline Press", "Push", "Chest") is True

    lock_query, lock_params = engine.conn.executed[0]
    query, params = engine.conn.executed[1]
    assert lock_query == "LOCK TABLE exercises IN EXCLUSIVE MODE"
    assert lock_params is None
    assert "exercise_id, exercise_name, category, body_part" in query
    assert "COALESCE(MAX(exercise_id), 0) + 1" in query
    assert "INSERT INTO exercise_muscle_map" in query
    assert "muscle_group" in query
    assert "set_factor" in query
    assert params == {
        "name": "Incline Press",
        "category": "Push",
        "body_part": "Chest",
    }
