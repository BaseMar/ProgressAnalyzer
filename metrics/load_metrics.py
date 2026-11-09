"""Shared load semantics for observations; never infer a convention from a name."""

from math import isclose, isfinite


def suggested_load_type(name):
    """Suggest entry/automation mode; never reinterpret recorded kilograms."""
    normalized = "".join(char for char in name.casefold() if char.isalnum())
    if any(
        term in normalized for term in ("deadhang", "pullup", "chinup", "dip", "hanginglegraise")
    ):
        if "machine" in normalized and "assisted" not in normalized:
            return "external"
        return "assisted_bodyweight" if "assisted" in normalized else "bodyweight"
    return "external"


def load_type(item):
    load = getattr(item, "load", None)
    return load.load_type if load is not None else "legacy"


def total_load_kg(item):
    load = getattr(item, "load", None)
    if load is not None:
        return load.total_load_kg
    value = getattr(item, "weight", None)
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value >= 0
        else None
    )


def load_record(item):
    load = getattr(item, "load", None)
    return {
        "load_type": load_type(item),
        "total_load_kg": total_load_kg(item),
        "body_mass_kg": load.body_mass_kg if load else None,
        "assistance_kg": load.assistance_kg if load else None,
    }


def recorded_load(item):
    """Legacy dictionaries remain compatible with their original recorded kg."""
    if "total_load_kg" not in item and item.get("load_type") in (
        "bodyweight",
        "assisted_bodyweight",
    ):
        return None
    return item.get("total_load_kg", item.get("weight"))


def load_comparison_problem(current, previous):
    if any(recorded_load(item) is None for item in (*current, *previous)):
        return "unknown_load"
    if any(
        now.get("load_type", "legacy") != old.get("load_type", "legacy")
        for now, old in zip(current, previous)
    ):
        return "load_convention_changed"
    return None


def same_loads(current, previous):
    return (
        len(current) == len(previous)
        and load_comparison_problem(current, previous) is None
        and all(
            isclose(recorded_load(now), recorded_load(old), rel_tol=0, abs_tol=1e-6)
            for now, old in zip(current, previous)
        )
    )


def describe_load(item):
    kind = item.get("load_type", "legacy")
    if kind in ("legacy", "external"):
        return f"{item['weight']:g} kg"
    body = item.get("body_mass_kg")
    support = item.get("assistance_kg")
    text = f"body {body:g} kg" if body is not None else "body mass unknown"
    text += f" + {item['weight']:g} kg"
    if kind == "assisted_bodyweight":
        text += f" − {support:g} kg assistance" if support is not None else " − unknown assistance"
    total = recorded_load(item)
    return text + (f" ≈ {total:g} kg total" if total is not None else " · total unknown")
