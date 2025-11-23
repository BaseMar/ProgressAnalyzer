from core.analytics.training import TrainingAnalytics


class KPIService:
    """Service layer that integrates analytics logic and returns ready-to-display KPIs."""

    def __init__(self, analytics: TrainingAnalytics):
        self.analytics = analytics

    def get_kpis(self) -> dict[str, object]:
        """Return a dictionary of KPIs for display on the dashboard."""

        return {
            "avg_intensity": self.analytics.weekly_agg("Intensity", "mean")["current"],
            "intensity_change": self.analytics.weekly_agg("Intensity", "mean")[
                "change"
            ],
            "total_volume": self.analytics.weekly_agg("Volume", "sum")["current"],
            "volume_change": self.analytics.weekly_agg("Volume", "sum")["change"],
            "avg_sets_per_session": self.analytics.weekly_agg(None, "sets_per_session")[
                "current"
            ],
            "sets_change": self.analytics.weekly_agg(None, "sets_per_session")[
                "change"
            ],
            "sessions": self.analytics.df_sets["SessionDate"].nunique(),
        }
