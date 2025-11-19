from core.analytics.training import TrainingAnalytics

class KPIService:
    """Łączy logikę z analytics i zwraca gotowe KPI do dashboardu."""

    def __init__(self, analytics: TrainingAnalytics):
        self.analytics = analytics

    def get_kpis(self) -> dict:
        """Zwraca słownik KPI do wyświetlenia na dashboardzie."""
        
        return {
            "avg_intensity": self.analytics.weekly_agg("Intensity", "mean")["current"],
            "intensity_change": self.analytics.weekly_agg("Intensity", "mean")["change"],
            "total_volume": self.analytics.weekly_agg("Volume", "sum")["current"],
            "volume_change": self.analytics.weekly_agg("Volume", "sum")["change"],
            "avg_sets_per_session": self.analytics.weekly_agg(None, "sets_per_session")["current"],
            "sets_change": self.analytics.weekly_agg(None, "sets_per_session")["change"],
            "sessions": self.analytics.df_sets["SessionDate"].nunique()
        }