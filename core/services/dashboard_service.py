from typing import Any, Dict, Optional, Tuple

from core.analytics.exercise import ExerciseAnalytics
from core.analytics.muscles import MuscleAnalytics


class DashboardService:
    """Service layer that wraps analytics objects for the UI.

    Purpose:
    - Keep UI code thin by exposing concise methods returning ready-to-render
      results (dataframes, KPI dicts, summaries).
    - Acts as the single integration point between UI and analytics logic.
    """

    def __init__(self, analytics: Any, kpi_service: Any) -> None:
        self.analytics: Any = analytics
        self.kpi_service: Any = kpi_service
        # exercise & muscles helper instances operate on the same df_sets
        self.exercise_analytics: ExerciseAnalytics = ExerciseAnalytics(
            analytics.df_sets
        )
        self.muscles: MuscleAnalytics = MuscleAnalytics(analytics.df_sets)

    def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Return KPIs for the main dashboard (delegates to KPI service)."""
        return self.kpi_service.get_kpis()

    def list_exercises(self) -> list[str]:
        return self.exercise_analytics.list_exercises()

    def get_exercise_analysis(self, exercise_name: str) -> Tuple[Any, Dict[str, Any], Any]:
        """Compute exercise-level artifacts used by the UI.

        Returns: (session_summary_df, kpis_dict, df_history)
        """
        df_ex = self.exercise_analytics.filter_exercise(exercise_name)
        session_summary = self.exercise_analytics.compute_session_summary(df_ex)
        kpis = self.exercise_analytics.compute_kpis(session_summary)
        df_history = self.exercise_analytics.compute_history_table(df_ex)
        return session_summary, kpis, df_history

    def get_muscle_data(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Tuple[MuscleAnalytics, Dict[str, Any], Any]:
        """Return a MuscleAnalytics instance (optionally filtered) and muscle-level kpis & summary."""
        muscles = self.muscles
        if date_from or date_to:
            muscles = muscles.filter_dates(date_from, date_to)
        kpis = muscles.muscle_kpis()
        summary = muscles.muscle_groups_summary()
        return muscles, kpis, summary
