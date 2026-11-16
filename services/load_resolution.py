"""Prepare explicit load snapshots for import and entry before transactional storage."""

from dataclasses import replace

import pandas as pd

from metrics.load_profiles import resolve_recorded_load


def prepare_load_entries(manager, exercises, workout_date):
    day = pd.Timestamp(workout_date).date()
    catalog = manager.load_exercise_load_catalog()
    by_name = {
        str(row["exercise_name"]).casefold().strip(): int(row["exercise_id"]) for row in catalog
    }
    profiles = manager.load_exercise_load_profiles(on_date=day)
    mass = None
    mass_read = False
    output = []
    for exercise in exercises:
        eid = exercise.get("exercise_id") or by_name.get(exercise["name"].casefold().strip())
        profile = profiles.get(eid)
        if profile is None:
            output.append(exercise)
            continue  # Exercise matching/creation still owns an unknown name.
        if profile.load_type != "external" and not mass_read:
            suggestion = manager.suggest_body_mass(day)
            mass = suggestion["weight"] if suggestion else None
            mass_read = True
        values = []
        for raw in exercise["sets"]:
            item = dict(raw)
            if item.get("load") is None:
                set_profile = profile
                mode = item.get("_weight_mode")
                if item.get("_assistance_kg") is not None:
                    set_profile = replace(
                        profile,
                        load_type="assisted_bodyweight",
                        input_mode="additional",
                        legacy_mode="unknown",
                    )
                    mode = mode or "additional"
                load = resolve_recorded_load(
                    set_profile,
                    float(item["weight"]),
                    body_mass=item.get("_body_mass_kg", mass),
                    assistance=item.get("_assistance_kg"),
                    mode=mode,
                )
                if load is None:
                    raise ValueError(
                        f"{exercise['name']}: body mass is needed to interpret total kilograms. Record additional weight with a + sign instead."
                    )
                item.update(load=load, weight=load.external_weight_kg)
            values.append(item)
        explicit_types = {item["load"].load_type for item in values if item.get("load") is not None}
        if (
            profile.source != "user"
            and len(explicit_types) == 1
            and profile.load_type not in explicit_types
        ):
            kind = next(iter(explicit_types))
            mode = {
                "external": "external",
                "bodyweight": "additional",
                "assisted_bodyweight": "assistance",
            }[kind]
            profile = replace(
                profile,
                load_type=kind,
                input_mode=mode,
                legacy_mode="external" if kind == "external" else "unknown",
                source="history",
            )
        output.append({**exercise, "exercise_id": eid, "sets": values, "load_profile": profile})
    return output
