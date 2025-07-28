from datetime import timedelta
from typing import List, Dict

def join_measurements_by_date(body_composition_list, body_measurements_list, tolerance_days=1):
    combined_results = []
    used_measurements = set()

    for comp in body_composition_list:
        comp_date = comp["DataPomiaru"]
        closest = None
        min_diff = timedelta(days=tolerance_days + 1)

        for i, meas in enumerate(body_measurements_list):
            if i in used_measurements:
                continue

            meas_date = meas["Data"]
            diff = abs(comp_date - meas_date)

            if diff <= timedelta(days=tolerance_days) and diff < min_diff:
                closest = (i, meas)
                min_diff = diff

        if closest:
            idx, matched_measurement = closest
            used_measurements.add(idx)

            combined_results.append({
                "Data": comp_date,
                **comp,
                **matched_measurement
            })

    return combined_results

def merge_body_data_with_tolerance(body_composition, body_measurements, max_days_diff=1):
    merged = []

    for comp in body_composition:
        data_comp = comp["DataPomiaru"]

        best_match = None
        min_diff = timedelta(days=max_days_diff + 1)

        for meas in body_measurements:
            data_meas = meas["DataPomiaru"]
            diff = abs(data_comp - data_meas)

            if diff <= timedelta(days=max_days_diff) and diff < min_diff:
                best_match = meas
                min_diff = diff

        if best_match:
            merged_record = {**comp, **best_match}
            merged.append(merged_record)

    return merged

def generate_combined_analysis(combined_data: list[dict]) -> str:
    if len(combined_data) < 2:
        return "Brak wystarczających danych do analizy porównawczej."

    before = combined_data[-2]
    after = combined_data[-1]

    lines = ["## Analiza postępu składu i obwodów ciała\n"]

    def compare(metric, label, unit=""):
        b, a = before.get(metric), after.get(metric)
        if b is None or a is None:
            return None

        diff = a - b
        if abs(diff) < 0.01:
            return f"• {label}: brak większych zmian ({a:.2f}{unit})"

        emoji = "⬆️" if diff > 0 else "⬇️"
        return f"• {label}: {emoji} {abs(diff):.2f}{unit} ({b:.2f} → {a:.2f}{unit})"

    comparisons = [
        ("Waga", "Waga", "kg"),
        ("MasaMiesniowa", "Masa mięśniowa", "kg"),
        ("MasaTluszczowa", "Masa tłuszczowa", "kg"),
        ("TkankaTluszczowa", "Tkanka tłuszczowa", "%"),
        ("ProcentWody", "Procent wody", "%"),
        ("Talia", "Obwód talii", "cm"),
        ("KlatkaPiersiowa", "Obwód klatki piersiowej", "cm"),
        ("Biodra", "Obwód bioder", "cm"),
        ("Udo", "Obwód uda", "cm"),
        ("Ramie", "Obwód ramienia", "cm"),
    ]

    for metric, label, unit in comparisons:
        result = compare(metric, label, unit)
        if result:
            lines.append(result)

    if before.get("TkankaTluszczowa") and after.get("TkankaTluszczowa"):
        fat_change = after["TkankaTluszczowa"] - before["TkankaTluszczowa"]
        if fat_change < -0.5:
            lines.append("\nMożliwa redukcja tkanki tłuszczowej – dobra robota!")
        elif fat_change > 0.5:
            lines.append("\nWzrost tkanki tłuszczowej – możliwe pogorszenie diety lub mniej ruchu.")

    if before.get("MasaMiesniowa") and after.get("MasaMiesniowa"):
        muscle_change = after["MasaMiesniowa"] - before["MasaMiesniowa"]
        if muscle_change > 0.5:
            lines.append("Przyrost masy mięśniowej – efekt treningu siłowego?")
        elif muscle_change < -0.5:
            lines.append("Spadek masy mięśniowej – możliwe przetrenowanie lub deficyt białka.")

    return "\n".join(lines)

def analyze_combined_ratios_over_time(combined_data: List[Dict]) -> List[str]:
    if len(combined_data) < 2:
        return ["Brakuje danych do śledzenia trendów. Potrzeba przynajmniej dwóch pomiarów."]

    combined_sorted = sorted(combined_data, key=lambda x: x['DataPomiaru'])

    trends = {
        "WHR": [],
        "R/Talia": [],
        "K/Talia": [],
        "Tluszcz %": [],
        "Mięśnie/Waga": []
    }

    for entry in combined_sorted:
        whr = entry["Talia"] / entry["Biodra"]
        r_talia = entry["Ramie"] / entry["Talia"]
        k_talia = entry["KlatkaPiersiowa"] / entry["Talia"]
        fat_pct = entry["TkankaTluszczowa"]
        muscle_ratio = entry["MasaMiesniowa"] / entry["Waga"]

        trends["WHR"].append(whr)
        trends["R/Talia"].append(r_talia)
        trends["K/Talia"].append(k_talia)
        trends["Tluszcz %"].append(fat_pct)
        trends["Mięśnie/Waga"].append(muscle_ratio)

    # Analiza trendów
    def trend_text(label, values, prefer='down' or 'up'):
        delta = values[-1] - values[0]
        direction = "spadł" if delta < 0 else "wzrósł"
        symbol = "⬇️" if delta < 0 else "⬆️"
        tendency = f"{symbol} {abs(delta):.2f}"
        comment = "✅ Dobry trend" if (delta < 0 and prefer == 'down') or (delta > 0 and prefer == 'up') else "⚠️ Możliwa regresja"
        return f"{label}: {direction} o {tendency}. {comment}"

    insights = [
        trend_text("WHR (talia/biodra)", trends["WHR"], prefer='down'),
        trend_text("Ramię/Talia", trends["R/Talia"], prefer='up'),
        trend_text("Klatka/Talia", trends["K/Talia"], prefer='up'),
        trend_text("Tkanka tłuszczowa (%)", trends["Tluszcz %"], prefer='down'),
        trend_text("Mięśnie/Waga", trends["Mięśnie/Waga"], prefer='up'),
    ]

    return insights

def compare_to_ideal(entry: Dict) -> List[str]:
    insights = []

    whr = entry["Talia"] / entry["Biodra"]
    if whr < 0.9:
        insights.append(f"✅ WHR = {whr:.2f} – bardzo dobry wskaźnik zdrowia metabolicznego.")
    else:
        insights.append(f"⚠️ WHR = {whr:.2f} – warto zadbać o redukcję tłuszczu brzusznego.")

    rt = entry["Ramie"] / entry["Talia"]
    if rt >= 0.5:
        insights.append(f"✅ Ramię / Talia = {rt:.2f} – estetyczny zarys sylwetki.")
    else:
        insights.append(f"⚠️ Ramię / Talia = {rt:.2f} – można wzmocnić górne partie ciała.")

    kt = entry["KlatkaPiersiowa"] / entry["Talia"]
    if kt >= 1.33:
        insights.append(f"✅ Klatka / Talia = {kt:.2f} – proporcje V-sylwetki.")
    else:
        insights.append(f"ℹ️ Klatka / Talia = {kt:.2f} – jeszcze nie pełna sylwetka V, ale blisko.")

    muscle_ratio = entry["MasaMiesniowa"] / entry["Waga"]
    if muscle_ratio >= 0.7:
        insights.append(f"✅ Masa mięśniowa stanowi {muscle_ratio:.2f} wagi – bardzo dobrze.")
    else:
        insights.append(f"ℹ️ Masa mięśniowa stanowi {muscle_ratio:.2f} wagi – można poprawić.")

    return insights
