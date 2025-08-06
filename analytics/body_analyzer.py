from typing import List, Dict

class BodyAnalyzer:
    def __init__(self, combined_data: List[Dict]):
        self.data = sorted(combined_data, key=lambda x: x["DataPomiaru"])
        self.latest = self.data[-1] if self.data else None

    def get_current_status(self) -> Dict[str, float]:
        """Zwraca aktualne wskaźniki i proporcje sylwetki (zaokrąglone do 2 miejsc)."""
        if not self.latest:
            return {}

        d = self.latest
        return {
            "Data": d["DataPomiaru"].strftime("%d.%m.%Y"),
            "Waga": round(d["Waga"], 2),
            "Tkanka tłuszczowa (%)": round(d["TkankaTluszczowa"], 2),
            "Masa mięśniowa (kg)": round(d["MasaMiesniowa"], 2),
            "WHR": round(d["Talia"] / d["Biodra"], 2),
            "Ramię / Talia": round(d["Ramie"] / d["Talia"], 2),
            "Klatka / Talia": round(d["KlatkaPiersiowa"] / d["Talia"], 2),
            "Mięśnie / Waga": round(d["MasaMiesniowa"] / d["Waga"], 2)
        }

    def summarize_measurements(self, df, metric: str)->Dict:
        """Wylicza średnią, wartość min/max dla obwodów i pomiaru ciała"""
        if df.empty or metric not in df.columns:
            return None

        metric_values = df[metric].dropna()
        if metric_values.empty:
            return None

        min_val = metric_values.min()
        max_val = metric_values.max()
        avg_val = metric_values.mean()
        percent_change = ((metric_values.iloc[-1] - metric_values.iloc[0]) / metric_values.iloc[0]) * 100 if len(metric_values) > 1 else 0
        trend_icon = "🔺" if percent_change > 0 else "🔻" if percent_change < 0 else "➖"

        return {
            "min": min_val,
            "max": max_val,
            "avg": avg_val,
            "percent_change": percent_change,
            "trend_icon": trend_icon
        }
    