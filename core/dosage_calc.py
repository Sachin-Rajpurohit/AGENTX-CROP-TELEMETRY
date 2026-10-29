"""Deterministic fertilizer and irrigation arithmetic. No LLM, no I/O.
Constants are passed in (they live in config/agronomy.yaml)."""
from __future__ import annotations

from math import ceil

HA_PER_ACRE = 0.404686
M2_PER_ACRE = 4046.86


def _nutrient(requirement, measured, supply, use_eff, oxide_factor, product_fraction):
    deficit = max(0.0, requirement - supply * measured)  # elemental kg/ha
    apply = deficit / use_eff                            # elemental kg/ha to apply
    oxide = apply * oxide_factor                         # P2O5 / K2O kg/ha (N: factor 1)
    product = oxide / product_fraction                   # fertilizer kg/ha
    return deficit, apply, oxide, product


def plan_fertilizer(measured: dict, requirement: dict, cfg: dict, area_acres: float) -> dict:
    """measured/requirement: {"N","P","K"} in kg/ha. Returns product amounts per ha and per area."""
    ha = area_acres * HA_PER_ACRE
    s, e, o = cfg["supply"], cfg["use_eff"], cfg["oxide"]
    d_n, a_n, _, _ = _nutrient(requirement["N"], measured["N"], s["N"], e["N"], 1.0, cfg["urea_n_fraction"])
    d_p, a_p, o_p, dap_ha = _nutrient(requirement["P"], measured["P"], s["P"], e["P"], o["P"], cfg["dap_p2o5_fraction"])
    d_k, a_k, o_k, mop_ha = _nutrient(requirement["K"], measured["K"], s["K"], e["K"], o["K"], cfg["mop_k2o_fraction"])

    dap_n_credit_ha = dap_ha * cfg["dap_n_fraction"]       # N (kg/ha) supplied by the DAP
    net_n_ha = max(0.0, a_n - dap_n_credit_ha)
    ha_vals = {
        "urea_gross": a_n / cfg["urea_n_fraction"],
        "urea_net": net_n_ha / cfg["urea_n_fraction"],
        "dap": dap_ha,
        "mop": mop_ha,
        "dap_n_credit_kg_n": dap_n_credit_ha,
    }
    return {
        "deficit_kg_ha": {"N": d_n, "P": d_p, "K": d_k},
        "apply_elemental_kg_ha": {"N": a_n, "P": a_p, "K": a_k},
        "oxide_kg_ha": {"P2O5": o_p, "K2O": o_k},
        "kg_ha": ha_vals,
        "kg_area": {k: v * ha for k, v in ha_vals.items()},
        "area_acres": area_acres,
    }


def irrigation_plan(vwc_now, trigger, root_depth_mm, area_acres, efficiency,
                    max_daily_mm, max_event_mm, refill_target=None, eff_rain_mm=0.0) -> dict:
    """Refill toward `refill_target` (default: trigger), capped per day and per event."""
    target = trigger if refill_target is None else refill_target
    if vwc_now >= trigger:
        return {"irrigate": False, "deficit_mm": 0.0, "daily_mm": 0.0, "events_per_day": 0,
                "litres_per_event": 0.0, "litres_per_day": 0.0, "days_to_refill": 0, "clipped": False}
    deficit_mm = max(0.0, (target - vwc_now) / 100 * root_depth_mm - eff_rain_mm)
    daily_mm = min(deficit_mm, max_daily_mm)
    events = max(1, ceil(daily_mm / max_event_mm)) if daily_mm > 0 else 0
    area_m2 = area_acres * M2_PER_ACRE                      # 1 mm over 1 m2 = 1 L
    litres_day = daily_mm / efficiency * area_m2
    return {
        "irrigate": daily_mm > 0, "deficit_mm": deficit_mm, "daily_mm": daily_mm,
        "events_per_day": events,
        "litres_per_event": litres_day / events if events else 0.0,
        "litres_per_day": litres_day,
        "days_to_refill": ceil(deficit_mm / max_daily_mm) if daily_mm > 0 else 0,
        "clipped": deficit_mm > max_daily_mm,
    }