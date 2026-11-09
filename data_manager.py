import logging
from datetime import date, time
from functools import wraps
from typing import Any, Dict, List

import pandas as pd

from db.connection import get_engine
from db.plan_adherence import (
    adherence_storage_ready,
    load_plan_adherence,
    load_plan_performance,
    remove_exercise_match,
    save_exercise_match,
)
from db.plan_schedule import (
    assign_scheduled_session,
    load_plan_session_links,
    load_scheduled_workout_targets,
    load_scheduled_workouts,
    plan_schedule_storage_ready,
    unassign_scheduled_session,
)
from db.queries import (
    delete_workout_session,
    get_all_sets,
    get_body_composition,
    get_body_measurements,
    get_exercise_muscle_targets,
    get_exercises,
    get_sets_raw,
    get_workout_exercises,
    get_workout_sessions,
    insert_body_composition,
    insert_body_measurements,
    insert_exercise,
)
from db.recommendation_references import load_recommendation_references
from db.set_classifications import (
    classification_storage_ready,
    load_session_sets,
    save_set_classifications,
)
from db.set_loads import save_session_set_loads, set_load_storage_ready, suggest_body_mass
from db.starting_loads import load_starting_loads, save_starting_loads, starting_load_storage_ready
from db.training_context import load_deload_exercise_ids
from db.training_plans import (
    load_effective_training_plan,
    load_training_plan_versions,
    load_training_plans,
    save_training_plan,
    training_plan_storage_ready,
)
from db.workout_sessions import save_workout_session
from models.training_plan import TrainingPlanDraft, TrainingPlanVersion
from services.recommendations import (
    load_workout_recommendations,
    prepare_plan_context,
    recommend_prepared_workout,
)

logger = logging.getLogger(__name__)


def _refresh_after_write(method):
    """Invalidate the shared input cache only after a successful database write."""

    @wraps(method)
    def wrapped(*args, **kwargs):
        result = method(*args, **kwargs)
        if result is not False:
            # Delayed import avoids the loader/manager dependency cycle.
            from data_loader import load_data

            load_data.clear()
        return result

    return wrapped


class DataManager:
    """UI-facing facade for storage and application services.

    SQL and transactions belong to db modules, recommendation orchestration to
    services, and domain conversion to mapper. Successful writes refresh input.
    """

    def __init__(self, *, engine=None):
        """Use the configured engine, or an explicit engine for isolated callers."""
        self.engine = get_engine() if engine is None else engine

    def load_sessions(self) -> pd.DataFrame:
        """Load all workout sessions from the database."""
        return get_workout_sessions(self.engine)

    def set_load_storage_ready(self):
        return set_load_storage_ready(self.engine)

    @_refresh_after_write
    def save_session_set_loads(self, session_id, values):
        return save_session_set_loads(self.engine, session_id, values)

    def suggest_body_mass(self, on_date):
        return suggest_body_mass(self.engine, on_date)

    def load_deload_exercise_ids(self, *, as_of=None):
        return load_deload_exercise_ids(self.engine, as_of=as_of)

    def classification_storage_ready(self):
        return classification_storage_ready(self.engine)

    def load_session_sets(self, session_id):
        return load_session_sets(self.engine, session_id)

    @_refresh_after_write
    def save_set_classifications(self, session_id, values):
        return save_set_classifications(self.engine, session_id, values)

    def plan_schedule_storage_ready(self):
        return plan_schedule_storage_ready(self.engine)

    def adherence_storage_ready(self):
        return adherence_storage_ready(self.engine)

    def load_plan_adherence(self, plan_id, start, end):
        return load_plan_adherence(self.engine, plan_id, start, end)

    def load_plan_performance(self, plan_id, start, end):
        return load_plan_performance(self.engine, plan_id, start, end)

    def prepare_plan_context(self, plan_id, start, end, *, as_of, versions=None):
        return prepare_plan_context(
            self.engine, plan_id, start, end, as_of=as_of, versions=versions
        )

    def recommend_prepared_workout(self, prepared, **options):
        return recommend_prepared_workout(self.engine, prepared, **options)

    def load_workout_recommendations(self, plan_id, day_id, scheduled_date, *, as_of, **options):
        return load_workout_recommendations(
            self.engine, plan_id, day_id, scheduled_date, as_of=as_of, **options
        )

    def load_recommendation_references(self, exercise_ids, *, as_of):
        return load_recommendation_references(self.engine, exercise_ids, as_of=as_of)

    def starting_load_storage_ready(self):
        return starting_load_storage_ready(self.engine)

    def load_starting_loads(self, upcoming, item, block):
        return load_starting_loads(self.engine, upcoming, item, block)

    @_refresh_after_write
    def save_starting_loads(self, upcoming, item, block, goals):
        return save_starting_loads(self.engine, upcoming, item, block, goals)

    @_refresh_after_write
    def save_exercise_match(self, session_id, plan_exercise_id, workout_exercise_id):
        return save_exercise_match(self.engine, session_id, plan_exercise_id, workout_exercise_id)

    @_refresh_after_write
    def remove_exercise_match(self, session_id, plan_exercise_id):
        return remove_exercise_match(self.engine, session_id, plan_exercise_id)

    def load_scheduled_workouts(self, plan_id, start, end):
        return load_scheduled_workouts(self.engine, plan_id, start, end)

    def load_scheduled_workout_targets(self, day_id):
        return load_scheduled_workout_targets(self.engine, day_id)

    def load_plan_session_links(self):
        return load_plan_session_links(self.engine)

    @_refresh_after_write
    def assign_scheduled_session(self, day_id, scheduled_date, session_id):
        return assign_scheduled_session(self.engine, day_id, scheduled_date, session_id)

    @_refresh_after_write
    def unassign_scheduled_session(self, day_id, scheduled_date, session_id):
        return unassign_scheduled_session(self.engine, day_id, scheduled_date, session_id)

    @_refresh_after_write
    def save_training_plan(
        self, draft: TrainingPlanDraft, *, plan_id: int | None = None
    ) -> TrainingPlanVersion:
        return save_training_plan(self.engine, draft, plan_id=plan_id)

    def training_plan_storage_ready(self) -> bool:
        return training_plan_storage_ready(self.engine)

    def load_training_plans(self) -> list[TrainingPlanVersion]:
        return load_training_plans(self.engine)

    def load_training_plan_versions(self, plan_id: int) -> list[TrainingPlanVersion]:
        return load_training_plan_versions(self.engine, plan_id)

    def load_effective_training_plan(
        self, plan_id: int, on_date: date
    ) -> TrainingPlanVersion | None:
        return load_effective_training_plan(self.engine, plan_id, on_date)

    def load_exercises(self) -> pd.DataFrame:
        """Load all exercises from the database."""
        return get_exercises(self.engine)

    def load_exercise_muscle_targets(self) -> pd.DataFrame:
        """Load detailed exercise-to-muscle mappings if the mapping table exists."""
        return get_exercise_muscle_targets(self.engine)

    def load_sets_ui(self) -> pd.DataFrame:
        """Sets prepared for UI (joins, names, volume)."""
        return get_all_sets(self.engine)

    def load_body_data(self) -> dict[str, pd.DataFrame]:
        """Load body measurements and body composition data.

        Returns a dict with keys 'measurements' and 'composition', each mapped to
        a DataFrame.
        """
        return {
            "measurements": get_body_measurements(self.engine),
            "composition": get_body_composition(self.engine),
        }

    @_refresh_after_write
    def add_exercise(
        self,
        name: str,
        category: str | None = None,
        body_part: str | None = None,
    ) -> bool:
        """Insert a new exercise into the database.

        Returns True on success, False on database error.
        """
        try:
            return insert_exercise(self.engine, name, category, body_part)
        except Exception as e:
            logger.exception("add_exercise failed: %s", e)
            return False

    def add_full_session(
        self,
        session_date: Any,
        notes: str,
        exercise_name: str,
        sets_data: List[Dict[str, Any]],
        session_start: time,
        session_end: time,
        *,
        exercise_id: int | None = None,
    ) -> bool:
        """Insert a complete workout session including exercise and sets.

        Returns True on success or re-raises the exception if the operation fails.
        """
        return self.add_workout_session(
            session_date,
            notes,
            [{"name": exercise_name, "exercise_id": exercise_id, "sets": sets_data}],
            session_start,
            session_end,
        )

    @_refresh_after_write
    def add_workout_session(
        self, session_date, notes, exercises_data, session_start=None, session_end=None
    ):
        """Persist a workout, then refresh the shared input cache."""
        return save_workout_session(
            self.engine, session_date, notes, exercises_data, session_start, session_end
        )

    @_refresh_after_write
    def add_body_measurements(self, data: dict) -> bool:
        """Insert body measurement records into the database.

        Returns True on success, False on database error.
        """
        try:
            insert_body_measurements(self.engine, data)
            return True
        except Exception as e:
            logger.exception("add_body_measurements failed: %s", e)
            return False

    @_refresh_after_write
    def add_body_composition(self, data: dict) -> bool:
        """Insert body composition records into the database.

        Returns True on success, False on database error.
        """
        try:
            insert_body_composition(self.engine, data)
            return True
        except Exception as e:
            logger.exception("add_body_composition failed: %s", e)
            return False

    def load_sets_raw(self) -> pd.DataFrame:
        """Raw workout sets for metrics (IDs only)."""
        return get_sets_raw(self.engine)

    def load_workout_exercises(self) -> pd.DataFrame:
        return get_workout_exercises(self.engine)

    @_refresh_after_write
    def delete_session(self, session_id: int) -> bool:
        try:
            return delete_workout_session(self.engine, session_id)
        except Exception:
            logger.exception("delete_session failed")
            return False
