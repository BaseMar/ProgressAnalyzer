"""Saved manual settings are defaults, never progression evidence."""
import hashlib
import json
from math import isfinite

from sqlalchemy import MetaData, func, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db.migrations.v008_starting_loads import define_table
from metrics.plan_performance import comparison_context
from models.progression import SetGoal

starting_loads = define_table(MetaData())
MANUAL_START_REASONS = frozenset({"no_history", "no_normal_baseline", "manual_start",
                                "changed_set_count", "history_gap"})


def starting_load_storage_ready(engine):
    with engine.connect() as connection:
        return inspect(connection).has_table(starting_loads.name)


def starting_load_key(upcoming, item, block):
    position, target = next((position, target) for position, target in enumerate(upcoming.targets, 1)
                            if target.plan_exercise_id == item.plan_exercise_id)
    # Dates of previews do not matter. New prescriptions, blocks, alternatives
    # and source executions require their own manual choice.
    context = (comparison_context(upcoming.slot, position, target.exercise, item.actual_exercise_id),
               target.exercise.weight_increment, block.cycle_start, item.reason_code,
               item.evidence_session_ids, item.evidence_dates)
    return hashlib.sha256(json.dumps(context, default=str).encode("utf-8")).hexdigest()


def load_starting_loads(engine, upcoming, item, block):
    if block.phase not in ("normal", "unconfigured") or item.reason_code not in MANUAL_START_REASONS:
        return ()
    key = starting_load_key(upcoming, item, block)
    with engine.connect() as connection:
        payload = connection.execute(select(starting_loads.c.loads_json).where(
            starting_loads.c.context_key == key)).scalar_one_or_none()
    if payload is None:
        return ()
    planned = next(t.exercise for t in upcoming.targets if t.plan_exercise_id == item.plan_exercise_id)
    return tuple(SetGoal(load["weight"], planned.target_min, planned.target_max, planned.target_unit,
                         load_type=load["load_type"], assistance_kg=load["assistance_kg"])
                 for load in json.loads(payload))


def save_starting_loads(engine, upcoming, item, block, goals):
    if block.phase not in ("normal", "unconfigured") or item.reason_code not in MANUAL_START_REASONS:
        raise ValueError("Starting loads require an ordinary manual-start recommendation")
    planned = next(t.exercise for t in upcoming.targets if t.plan_exercise_id == item.plan_exercise_id)
    def valid_load(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0
    if len(goals) != planned.set_count or any(
        not valid_load(g.weight) or g.load_type not in ("external", "bodyweight", "assisted_bodyweight")
        or (g.assistance_kg is not None and not valid_load(g.assistance_kg))
        or (g.load_type == "assisted_bodyweight" and g.assistance_kg is None) for g in goals
    ):
        raise ValueError("Enter a valid load for every working set, including required assistance")
    key = starting_load_key(upcoming, item, block)
    payload = json.dumps([dict(weight=g.weight, load_type=g.load_type, assistance_kg=g.assistance_kg) for g in goals])
    # Both supported databases provide atomic upserts, including simultaneous tabs.
    with engine.begin() as connection:
        insert = sqlite_insert if connection.dialect.name == "sqlite" else pg_insert
        statement = insert(starting_loads).values(context_key=key, loads_json=payload)
        connection.execute(statement.on_conflict_do_update(index_elements=[starting_loads.c.context_key],
            set_={"loads_json": payload, "updated_at": func.current_timestamp()}))
