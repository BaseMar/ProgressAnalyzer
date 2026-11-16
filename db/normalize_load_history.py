"""Audit/normalize old load conventions with originals retained; default is read-only."""

import argparse
from datetime import date

import pandas as pd
from sqlalchemy import String, bindparam, cast, select, update

from db.load_profiles import (
    catalog,
    originals,
    profiles,
    resolved_profiles,
    sessions,
    store_profile,
)
from db.read_cache import has_table
from db.recorded_workouts import actual_exercises, actual_sets
from db.set_loads import loads, measurements
from metrics.load_profiles import resolve_recorded_load


def _body_history(connection):
    if not has_table(connection, measurements.name):
        return ()
    result = []
    for stamp, weight in connection.execute(
        select(cast(measurements.c.measurement_date, String), measurements.c.weight)
    ):
        try:
            stamp = pd.Timestamp(stamp)
            weight = float(weight)
            if pd.notna(stamp) and 0 < weight < float("inf"):
                result.append((stamp.tz_localize(None), weight))
        except (TypeError, ValueError, OverflowError):
            continue
    return tuple(sorted(result))


def _plan(connection, *, as_of, exercise_ids=None):
    if not has_table(connection, profiles.name):
        raise ValueError("Apply database migration 011 before normalizing history")
    resolved = resolved_profiles(connection, on_date=as_of, exercise_ids=exercise_ids)
    body = _body_history(connection)
    query = (
        select(
            actual_sets.c.set_id,
            actual_sets.c.weight,
            catalog.c.exercise_id,
            catalog.c.exercise_name,
            sessions.c.session_date,
        )
        .join(
            actual_exercises,
            actual_exercises.c.workout_exercise_id == actual_sets.c.workout_exercise_id,
        )
        .join(catalog, catalog.c.exercise_id == actual_exercises.c.exercise_id)
        .join(sessions, sessions.c.session_id == actual_exercises.c.session_id)
        .outerjoin(loads, loads.c.set_id == actual_sets.c.set_id)
        .outerjoin(originals, originals.c.set_id == actual_sets.c.set_id)
        .where(
            loads.c.set_id.is_(None),
            originals.c.set_id.is_(None),
            catalog.c.exercise_id.in_(resolved),
        )
        .order_by(catalog.c.exercise_id, actual_sets.c.set_id)
    )
    if connection.dialect.name == "postgresql":
        query = query.with_for_update(of=actual_sets)
    changes, summary = [], {}
    for row in connection.execute(query).mappings():
        day = pd.Timestamp(row["session_date"]).date()
        if day > as_of:
            continue
        profile = resolved[row["exercise_id"]]
        item = summary.setdefault(
            profile.exercise_id,
            {
                "exercise_id": profile.exercise_id,
                "exercise": row["exercise_name"],
                "load_type": profile.load_type,
                "legacy_mode": profile.legacy_mode,
                "convertible": 0,
                "unresolved": 0,
            },
        )
        mass = next(
            (weight for measured_on, weight in reversed(body) if measured_on.date() <= day), None
        )
        try:
            load = resolve_recorded_load(
                profile, row["weight"], body_mass=mass, mode=profile.legacy_mode
            )
        except ValueError:
            load = None
        if load is None:
            item["unresolved"] += 1
        else:
            item["convertible"] += 1
            changes.append((row["set_id"], row["weight"], load))
    return resolved, list(summary.values()), changes


def audit_history(engine, *, as_of=None, exercise_ids=None):
    with engine.connect() as connection:
        _, summary, changes = _plan(
            connection, as_of=as_of or date.today(), exercise_ids=exercise_ids
        )
    return {
        "exercises": summary,
        "convertible": len(changes),
        "unresolved": sum(row["unresolved"] for row in summary),
    }


def normalize_history(engine, *, as_of=None, exercise_ids=None, overrides=()):
    """Archive and normalize only unspecified sets, atomically and idempotently."""
    with engine.begin() as connection:
        for profile in overrides:
            if exercise_ids is not None and profile.exercise_id not in exercise_ids:
                raise ValueError("Profile override is outside the selected exercises")
            store_profile(connection, profile)
        resolved, summary, changes = _plan(
            connection, as_of=as_of or date.today(), exercise_ids=exercise_ids
        )
        for profile in resolved.values():
            store_profile(connection, profile)
        if changes:
            connection.execute(
                originals.insert(),
                [
                    {
                        "set_id": sid,
                        "weight": weight,
                        "load_type": None,
                        "body_mass_kg": None,
                        "assistance_kg": None,
                        "normalized_weight": load.external_weight_kg,
                        "normalized_load_type": load.load_type,
                        "normalized_body_mass_kg": load.body_mass_kg,
                        "normalized_assistance_kg": load.assistance_kg,
                    }
                    for sid, weight, load in changes
                ],
            )
            connection.execute(
                loads.insert(),
                [
                    {
                        "set_id": sid,
                        "load_type": load.load_type,
                        "body_mass_kg": load.body_mass_kg,
                        "assistance_kg": load.assistance_kg,
                    }
                    for sid, _, load in changes
                ],
            )
            updates = [
                {"target_set_id": sid, "new_weight": load.external_weight_kg}
                for sid, weight, load in changes
                if weight != load.external_weight_kg
            ]
            if updates:
                connection.execute(
                    update(actual_sets)
                    .where(actual_sets.c.set_id == bindparam("target_set_id"))
                    .values(weight=bindparam("new_weight")),
                    updates,
                )
    return {
        "exercises": summary,
        "converted": len(changes),
        "unresolved": sum(row["unresolved"] for row in summary),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    from db.connection import get_engine

    result = normalize_history(get_engine()) if args.apply else audit_history(get_engine())
    for row in result["exercises"]:
        print(
            f"{row['exercise_id']}: {row['exercise']} · {row['load_type']} · {row['convertible']} convertible · {row['unresolved']} unresolved"
        )
    print({key: value for key, value in result.items() if key != "exercises"})


if __name__ == "__main__":
    main()
