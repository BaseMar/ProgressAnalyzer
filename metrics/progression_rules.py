"""One-session decisions, independent of storage, calendar and presentation."""
from decimal import Decimal, ROUND_FLOOR
from dataclasses import replace
from math import isclose, isfinite

from models.progression import SetGoal


def set_goal(item, minimum, maximum=None, *, weight=None, unit="reps"):
    return SetGoal(item["weight"] if weight is None else weight, minimum,
                   minimum if maximum is None else maximum, unit,
                   item.get("load_type", "legacy"), item.get("assistance_kg"))


def weight_step_problem(step):
    if step is None:
        return "missing_weight_step", "Set the actual exercise's available weight step."
    if isinstance(step, bool) or not isinstance(step, (int, float)) or not isfinite(step) or step <= 0:
        return "invalid_weight_step", "The actual exercise's weight step must be finite and positive."
    return None


def session_decision(planned, sets, step, policy, *, manual_load=False):
    """Return action, reason code, explanation and immutable per-set targets."""
    timed = planned.target_unit == "seconds"
    field = "seconds" if timed else "reps"
    quantities = [min(max(int(item[field]), planned.target_min), planned.target_max) for item in sets]

    def goals(values=None, weights=None):
        result = tuple(set_goal(item, (values or quantities)[i],
            weight=weights[i] if weights is not None else None, unit=planned.target_unit)
            for i, item in enumerate(sets))
        return tuple(replace(goal, weight=None, load_type="manual_bodyweight")
                     if manual_load and item.get("load_type", "legacy") == "legacy" else goal
                     for goal, item in zip(result, sets))

    def result(action, code, reason, target=None):
        target = goals() if target is None else tuple(target)
        if manual_load:
            target = tuple(replace(g, weight=None, load_type="manual_bodyweight")
                if s.get("load_type", "legacy") == "legacy" else g for g,s in zip(target,sets))
        return action, code, reason, target

    if timed:
        if any(item[field] < planned.target_min for item in sets):
            return result("maintain", "time_below_range", "Keep the time range and choose a manageable duration; do not add time below the minimum.")
        index = next((i for i, value in enumerate(quantities) if value < planned.target_max), None)
        if index is None:
            return result("maintain", "time_ceiling_manual", "The time ceiling is reached. Choose a new time range or load manually; seconds are not converted into kilograms.")
        quantities[index] = min(planned.target_max, quantities[index] + policy.timed_increment_seconds)
        return result("increase_time", "more_time", "Try up to five additional seconds in one set within the range; retain the logged load or assistance setting.")

    bodyweight = manual_load or any(item.get("load_type") in ("bodyweight", "assisted_bodyweight") for item in sets)
    failures = [i for i, item in enumerate(sets)
                if (item["reps"] <= planned.target_min and item["rir"] < planned.target_rir)
                or (item["reps"] < planned.target_min and item["rir"] <= planned.target_rir)]
    if failures:
        if bodyweight:
            return result("maintain", "bodyweight_load_manual", "The minimum was not achieved with the planned reserve. Choose added load or assistance manually; less assistance increases difficulty.")
        problem = weight_step_problem(step)
        if problem:
            return "insufficient_data", *problem, ()
        weights = [item["weight"] for item in sets]
        for index in failures:
            weight = weights[index]
            if weight <= 0 or step >= weight:
                return result("maintain", "reduction_step_not_supported", "The minimum needs correction, but no positive lower equipment setting is available. Choose that set's load manually.")
            weights[index] = float(Decimal(str(weight)) - Decimal(str(step)))
            quantities[index] = planned.target_min
        return result("reduce_weight", "minimum_not_met", "After the first failure at the minimum, reduce only the affected set by one equipment step. Other set loads are retained.", goals(weights=weights))

    if any(item["rir"] < planned.target_rir for item in sets):
        return result("maintain", "rir_below_target", "Keep the load and planned range; finish earlier within that range to meet the reserve before increasing difficulty.",
            [set_goal(item, planned.target_min, planned.target_max) for item in sets])
    if any(item["reps"] < planned.target_min for item in sets):
        return result("maintain", "below_range", "Complete the planned range with the required reserve before adding another repetition.",
            [set_goal(item, planned.target_min, planned.target_max) for item in sets])

    weights = [item["weight"] for item in sets]
    anchor = weights[0]
    if not bodyweight and any(weight > anchor + 1e-6 for weight in weights[1:]):
        return "insufficient_data", "manual_start", "Loads rose after the first set. Review the history and choose the working start manually; a later heavier trial does not establish it.", ()

    index = next((i for i, value in enumerate(quantities) if value < planned.target_max), None)
    if index is not None:
        quantities[index] += 1
        return result("increase_reps", "one_more_rep", "Try one additional total repetition in the first set below the upper bound; keep each set's load and the planned reserve.")

    if bodyweight:
        return result("maintain", "bodyweight_load_manual", "All repetition targets were reached. Choose added weight or assistance manually; future body mass is not assumed.")
    if anchor <= 0:
        return result("maintain", "zero_load", "The repetition ceiling is reached; adding external load to a zero-load exercise requires manual selection.")
    problem = weight_step_problem(step)
    if problem:
        return "insufficient_data", *problem, ()

    if any(not isclose(weight, anchor, rel_tol=0, abs_tol=1e-6) for weight in weights):
        next_weights = weights.copy()
        for i, weight in enumerate(weights):
            if isclose(weight, anchor, rel_tol=0, abs_tol=1e-6):
                continue
            load, increment = Decimal(str(weight)), Decimal(str(step))
            allowed = min(Decimal(str(anchor)) - load,
                          load * Decimal(str(policy.max_relative_weight_increase)))
            steps = (allowed / increment).to_integral_value(rounding=ROUND_FLOOR)
            if steps >= 1:
                next_weights[i] = float(load + steps * increment)
                quantities[i] = planned.target_min
        if next_weights == weights:
            return result("maintain", "weight_step_not_supported", "Equalization needs a smaller available equipment step within the 10% per-set limit. Choose the next setting manually.")
        return result("equalize_weight", "equalize_loads", "Every set reached its ceiling with enough reserve. Bring lighter sets toward the established first-set load in available steps within 10%; reset repetitions only in the raised sets.", goals(weights=next_weights))

    if step / anchor > policy.max_relative_weight_increase:
        return result("maintain", "weight_step_not_supported", "The next available common load exceeds the 10% step limit. Choose a smaller equipment step or a new range manually.")
    next_weight = float(Decimal(str(anchor)) + Decimal(str(step)))
    return result("increase_weight", "upper_range_confirmed", "All sets reached the upper bound at one common load with enough reserve. One complete execution is sufficient: add one equipment step and start at the lower bound.",
        [set_goal(item, planned.target_min, weight=next_weight) for item in sets])
