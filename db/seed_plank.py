from __future__ import annotations

from sqlalchemy import text

from db.connection import get_engine
from db.exercise_muscle_resolver import resolve_exercise


def main() -> None:
    resolution = resolve_exercise("Plank", allow_web=False)
    if resolution is None:
        raise RuntimeError("Could not resolve Plank muscle targets.")

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE workout_sets ADD COLUMN IF NOT EXISTS duration_seconds INTEGER")
        )

        duration_constraint_exists = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'workout_sets_duration_seconds_positive'
                """
            )
        ).scalar()
        if not duration_constraint_exists:
            conn.execute(
                text(
                    """
                    ALTER TABLE workout_sets
                    ADD CONSTRAINT workout_sets_duration_seconds_positive
                    CHECK (duration_seconds IS NULL OR duration_seconds > 0)
                    """
                )
            )

        exercise_id = conn.execute(
            text(
                """
                SELECT exercise_id
                FROM exercises
                WHERE lower(exercise_name) = lower(:name)
                """
            ),
            {"name": "Plank"},
        ).scalar()

        if exercise_id is None:
            conn.execute(text("LOCK TABLE exercises IN EXCLUSIVE MODE"))
            exercise_id = conn.execute(
                text(
                    """
                    INSERT INTO exercises (exercise_id, exercise_name, category, body_part)
                    VALUES (
                        (SELECT COALESCE(MAX(exercise_id), 0) + 1 FROM exercises),
                        :name,
                        :category,
                        :body_part
                    )
                    RETURNING exercise_id
                    """
                ),
                {
                    "name": "Plank",
                    "category": resolution.category,
                    "body_part": resolution.body_part,
                },
            ).scalar_one()

        for target in resolution.targets:
            conn.execute(
                text(
                    """
                    INSERT INTO exercise_muscle_map
                        (exercise_id, muscle_group, muscle_name, role, set_factor, source_note)
                    VALUES
                        (:exercise_id, :muscle_group, :muscle_name, :role, :set_factor, :source_note)
                    ON CONFLICT (exercise_id, muscle_group) DO UPDATE
                    SET
                        muscle_name = EXCLUDED.muscle_name,
                        role = EXCLUDED.role,
                        set_factor = EXCLUDED.set_factor,
                        source_note = EXCLUDED.source_note,
                        updated_at = now()
                    """
                ),
                {
                    "exercise_id": exercise_id,
                    "muscle_group": target.muscle_group,
                    "muscle_name": target.muscle_name,
                    "role": target.role,
                    "set_factor": target.set_factor,
                    "source_note": target.source_note,
                },
            )

    print(f"Seeded Plank exercise with duration support as exercise_id={exercise_id}.")


if __name__ == "__main__":
    main()
