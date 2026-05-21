from db.queries import insert_exercise


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class _Connection:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((str(query), params))
        if "RETURNING exercise_id" in str(query):
            return _Result(53)
        return _Result(None)


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
    exercise_query, exercise_params = engine.conn.executed[1]
    muscle_query, muscle_params = engine.conn.executed[2]
    assert lock_query == "LOCK TABLE exercises IN EXCLUSIVE MODE"
    assert lock_params is None
    assert "exercise_id, exercise_name, category, body_part" in exercise_query
    assert "COALESCE(MAX(exercise_id), 0) + 1" in exercise_query
    assert exercise_params == {
        "name": "Incline Press",
        "category": "Push",
        "body_part": "Chest",
    }
    assert "INSERT INTO exercise_muscle_map" in muscle_query
    assert "muscle_group" in muscle_query
    assert "set_factor" in muscle_query
    assert {row["muscle_group"] for row in muscle_params} == {
        "Chest",
        "Shoulders",
        "Triceps",
    }


def test_insert_exercise_resolves_t_bar_row_as_compound_pull():
    engine = _Engine()

    assert insert_exercise(engine, "T-Bar Row") is True

    exercise_params = engine.conn.executed[1][1]
    muscle_params = engine.conn.executed[2][1]
    assert exercise_params == {
        "name": "T-Bar Row",
        "category": "Pull",
        "body_part": "Back",
    }
    assert {row["muscle_group"] for row in muscle_params} == {
        "Back",
        "Shoulders",
        "Biceps",
        "Forearms",
        "Lower Back",
    }
    assert next(row for row in muscle_params if row["muscle_group"] == "Back")["role"] == "primary"
    assert next(row for row in muscle_params if row["muscle_group"] == "Biceps")["role"] == "secondary"
