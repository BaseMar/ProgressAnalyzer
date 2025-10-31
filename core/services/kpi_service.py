from core.analytics import TrainingAnalytics

class KPIService:
    """Łączy logikę z analytics i zwraca gotowe KPI do dashboardu."""

    def __init__(self, analytics: TrainingAnalytics):
        self.analytics = analytics

    def get_kpis(self) -> dict:
        """Zwraca słownik KPI do wyświetlenia na dashboardzie."""
        base = self.analytics.kpi_summary()
        weekly_volume = self.analytics.weekly_agg("Volume", agg_func="sum")
        weekly_intensity = self.analytics.weekly_agg("Intensity", agg_func="mean")

        return {
            "avg_intensity": base["avg_intensity"],
            "intensity_change": weekly_intensity["change"],
            "total_volume": weekly_volume["current"],
            "volume_change": weekly_volume["change"],
            "sessions": base["sessions"],
        }