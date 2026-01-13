from typing import Any, Dict

from core.models import WorkoutExercise, WorkoutSession
from metrics.metrics_engine import compute_all_metrics
from metrics.input import MetricsInput
from core.data_manager import DataManager
from models.body_composition import BodyComposition
from models.body_measurement import BodyMeasurement
from models.exercise import Exercise
from models.workout_set import WorkoutSet


class DashboardService:
    """
    Service layer responsible for computing and exposing all dashboard metrics.

    Acts as the integration layer between:
    - database (DataManager)
    - metrics engine
    - UI
    """

    def __init__(self, data_manager: DataManager) -> None:
        self.data_manager = data_manager

    def compute_dashboard_metrics(self) -> Dict[str, dict]:
        """
        Load all required data, compute metrics and return results
        ready for UI consumption.
        """

        metrics_input = self._build_metrics_input()
        return compute_all_metrics(metrics_input)

    def _build_metrics_input(self) -> MetricsInput:
        """
        Load raw data from the database and construct MetricsInput.
        """

        # --- load raw data ---
        sessions_df = self.data_manager.load_sessions()
        exercises_df = self.data_manager.load_exercises()
        sets_df = self.data_manager.load_sets()
        body_data = self.data_manager.load_body_data()

        # --- map DataFrames -> domain models ---
        sessions = [WorkoutSession(
                session_id=row.SessionID,
                session_date=row.SessionDate,
                start_time=row.StartTime,
                end_time=row.EndTime,)
            for _, row in sessions_df.iterrows()]

        exercises = [
            Exercise(
                exercise_id=row.ExerciseID,
                name=row.ExerciseName,
                primary_muscle_group_id=row.PrimaryMuscleGroupID, )
            for _, row in exercises_df.iterrows()]

        workout_exercises = [
            WorkoutExercise(
                workout_exercise_id=row.WorkoutExerciseID,
                session_id=row.SessionID,
                exercise_id=row.ExerciseID,)
            for _, row in sets_df.drop_duplicates("WorkoutExerciseID").iterrows()]

        sets = [
            WorkoutSet(
                workout_exercise_id=row.WorkoutExerciseID,
                set_number=row.SetNumber,
                repetitions=row.Repetitions,
                weight=row.Weight,
                rir=row.RIR,
            )
            for _, row in sets_df.iterrows()
        ]

        body_measurements = [
            BodyMeasurement(
                date=row.Date,
                measurement_type=row.Type,
                value=row.Value,)
            for _, row in body_data["measurements"].iterrows()]

        body_composition = [
            BodyComposition(
                date=row.Date,
                weight=row.Weight,
                fat_percentage=row.FatPercentage,)
            for _, row in body_data["composition"].iterrows()]

        return MetricsInput(
            sessions=sessions,
            workout_exercises=workout_exercises,
            sets=sets,
            exercises=exercises,
            muscle_groups=[],
            body_measurements=body_measurements,
            body_composition=body_composition,
        )
