from core.data_manager import DataManager
import pandas as pd

class BodyMetricsService:

    def __init__(self):
        self.dm = DataManager()

    def get_body_data(self):
        raw = self.dm.load_body_data()
        measurements = raw.get("measurements")
        composition = raw.get("composition")

        measurements = self._prepare(measurements)
        composition = self._prepare(composition)

        kpis = self._compute_kpis(composition)

        return {
            "measurements": measurements,
            "composition": composition,
            "kpis": kpis,
        }

    def _prepare(self, df):
        if df is None or df.empty:
            return None

        df = df.copy()

        if "MeasurementDate" in df.columns:
            df["MeasurementDate"] = pd.to_datetime(df["MeasurementDate"])

        return df

    def _compute_kpis(self, comp):
        if comp is None or comp.empty:
            return [
                {"title": "Weight", "value": "—", "delta": None},
                {"title": "Muscle Mass", "value": "—", "delta": None},
                {"title": "Body Fat %", "value": "—", "delta": None},
            ]

        comp = comp.sort_values("MeasurementDate")
        latest = comp.iloc[-1]
        prev = comp.iloc[-2] if comp.shape[0] > 1 else None

        def delta(curr, prev):
            if prev is None or pd.isna(curr) or pd.isna(prev):
                return None
            return f"{float(curr) - float(prev):+.1f}"

        return [
            {
                "title": "Weight",
                "value": f"{latest.get('Weight'):0.1f} kg",
                "delta": delta(latest.get("Weight"), prev.get("Weight") if prev is not None else None)
            },
            {
                "title": "Muscle Mass",
                "value": f"{latest.get('MuscleMass'):0.1f} kg",
                "delta": delta(latest.get("MuscleMass"), prev.get("MuscleMass") if prev is not None else None)
            },
            {
                "title": "Body Fat %",
                "value": f"{latest.get('BodyFatPercentage'):0.1f}%",
                "delta": delta(latest.get("BodyFatPercentage"), prev.get("BodyFatPercentage") if prev is not None else None)
            },
        ]

    def _compute_metric_stats(self, df: pd.DataFrame, col: str):
        """Compute stats: latest, min, max, average, trend from first value"""
        if df is None or df.empty or col not in df.columns:
            return {
                "latest": None,
                "min": None,
                "max": None,
                "avg": None,
                "trend": None,
            }
        series = df[col].dropna().sort_index()  # sort by date
        if series.empty:
            return {"latest": None, "min": None, "max": None, "avg": None, "trend": None}

        latest = series.iloc[-1]
        min_val = series.min()
        max_val = series.max()
        avg_val = series.mean()
        trend = latest - series.iloc[0]

        return {
            "latest": latest,
            "min": min_val,
            "max": max_val,
            "avg": avg_val,
            "trend": trend,
        }
