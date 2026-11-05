"""Compact formatting for recorded set snapshots in Analysis."""

from metrics.load_metrics import recorded_load


def recorded_set_value(item, unit):
    quantity = item["seconds"] if unit == "seconds" else item["reps"]
    suffix = "s" if unit == "seconds" else "reps"
    load = recorded_load(item)
    if load is None:
        return f"? kg × {quantity:g} {suffix}"
    total = " total" if item.get("load_type") in ("bodyweight", "assisted_bodyweight") else ""
    return f"{load:g} kg{total} × {quantity:g} {suffix}"
