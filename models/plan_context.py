"""Immutable read inputs shared by plan presentation and recommendations."""

from dataclasses import dataclass
from datetime import date

from models.plan_adherence import PlanAdherenceInput, PlannedWorkout
from models.training_plan import TrainingPlanVersion


@dataclass(frozen=True)
class PreparedWorkout:
    history: PlanAdherenceInput
    upcoming: PlannedWorkout
    versions: tuple[TrainingPlanVersion, ...]
    as_of: date

    @property
    def settings_by_version(self):
        return {version.version_id: version.draft.progression for version in self.versions}


@dataclass(frozen=True)
class PlanReadContext:
    plan_id: int
    as_of: date
    versions: tuple[TrainingPlanVersion, ...]
    history: PlanAdherenceInput

    def prepare_workout(self, day_id: int, scheduled_date: date) -> PreparedWorkout:
        upcoming = next(
            (
                item
                for item in self.history.workouts
                if item.slot.day_id == day_id and item.slot.scheduled_date == scheduled_date
            ),
            None,
        )
        if upcoming is None:
            raise ValueError("This workout is not scheduled for the selected plan and date")
        return PreparedWorkout(self.history, upcoming, self.versions, self.as_of)
