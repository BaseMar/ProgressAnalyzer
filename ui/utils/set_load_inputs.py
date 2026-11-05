"""Shared load controls for manual entry, import review and history corrections."""
import streamlit as st

from models.set_load import SetLoad
from ui.utils.exercise_matcher import normalize

LOAD_LABELS = {
    "legacy": "Original log", "external": "External weight",
    "bodyweight": "Bodyweight", "assisted_bodyweight": "Assisted bodyweight",
}


def suggested_load_type(name):
    name = "".join(normalize(name).split())
    if any(term in name for term in ("deadhang", "pullup", "chinup", "dip")):
        if "machine" in name and "assisted" not in name:
            return "external"
        return "assisted_bodyweight" if "assisted" in name else "bodyweight"
    return "external"


def render_load_inputs(manager, workout_date, *, key, current=None, default="legacy", allow_legacy=True):
    options = list(LOAD_LABELS) if allow_legacy else list(LOAD_LABELS)[1:]
    kind = st.selectbox("Load type", options, index=options.index(default),
                        format_func=LOAD_LABELS.get, key=f"{key}_kind")
    if kind == "legacy":
        st.caption("Keep the file's recorded kg values. Select Bodyweight only when kg means additional weight.")
        return kind, None, None
    if kind == "external":
        return kind, None, 0.0
    suggestion = manager.suggest_body_mass(workout_date)
    initial = current.body_mass_kg if current is not None and current.load_type == kind else (
        suggestion["weight"] if suggestion else None)
    # A different workout date must refresh the measurement suggestion.
    body = st.number_input("Body mass (kg)", min_value=0.1, value=initial, step=0.1,
                           key=f"{key}_{workout_date}_{kind}_body", format="%.1f")
    if suggestion:
        st.caption(f"Latest measurement on/before this workout: {suggestion['weight']:g} kg "
                   f"on {suggestion['date']:%Y-%m-%d}. You can edit the value saved with these sets.")
    else:
        st.caption("No earlier body-mass measurement. Enter a value or leave it unknown.")
    assistance = 0.0
    if kind == "assisted_bodyweight":
        initial_assistance = current.assistance_kg if current is not None and current.load_type == kind else None
        assistance = st.number_input("Assistance (kg)", min_value=0.1, value=initial_assistance,
            step=0.5, key=f"{key}_assistance", help="Measured counterweight. Leave blank for unknown support, such as an unmeasured resistance band.")
    st.caption("The kg column records additional weight. Body mass is saved separately for this workout.")
    return kind, body, assistance


def make_set_load(settings, external_weight):
    kind, body, assistance = settings
    if kind == "legacy":
        return None
    try:
        weight = float(external_weight)
    except (TypeError, ValueError):
        raise ValueError("Enter a non-negative weight for every set") from None
    return SetLoad(kind, weight, body, assistance)


def render_total_loads(settings, weights):
    if settings[0] == "legacy":
        return
    totals = []
    for weight in weights:
        total = make_set_load(settings, weight).total_load_kg
        totals.append("unknown" if total is None else f"≈ {total:g} kg")
    st.caption("Total load by set: " + " / ".join(totals))


def format_load(load):
    if load.load_type == "external":
        return f"{load.external_weight_kg:g} kg"
    body = "unknown" if load.body_mass_kg is None else f"{load.body_mass_kg:g} kg"
    text = f"body {body} + {load.external_weight_kg:g} kg"
    if load.load_type == "assisted_bodyweight":
        support = "unknown" if load.assistance_kg is None else f"{load.assistance_kg:g} kg"
        text += f" − {support} assistance"
    total = load.total_load_kg
    return text + (" · total unknown" if total is None else f" ≈ {total:g} kg total")
