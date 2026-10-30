"""Config-driven wrappers around core.dosage_calc (which holds the verified arithmetic)."""
from __future__ import annotations

from core.dosage_calc import irrigation_plan, plan_fertilizer

IRRIGATION_METHODS = ("drip", "flood")


def fertilizer_calc_cfg(cfg: dict) -> dict:
    """Translate agronomy.yaml keys into the dict plan_fertilizer expects."""
    return {
        "supply": {"N": 1.0, "P": 1.0, "K": 1.0},
        "use_eff": {"N": cfg["use_eff_N"], "P": cfg["use_eff_P"], "K": cfg["use_eff_K"]},
        "oxide": {"P": cfg["p_to_p2o5"], "K": cfg["k_to_k2o"]},
        "urea_n_fraction": cfg["urea_pct"],
        "dap_p2o5_fraction": cfg["dap_p2o5_pct"],
        "dap_n_fraction": cfg["dap_n_pct"],
        "mop_k2o_fraction": cfg["mop_k2o_pct"],
    }


def nutrient_dose(measured: dict, requirement: dict, area_acres: float, cfg: dict) -> dict:
    """Urea / DAP / MOP for N/P/K measured vs stage requirement (both kg/ha)."""
    return plan_fertilizer(measured, requirement, fertilizer_calc_cfg(cfg), area_acres)


def effective_rain_mm(rain_mm_48h: float, rain_prob_48h: float, cfg: dict) -> float:
    """Rain counts toward the water deficit only when it is likely."""
    if rain_prob_48h >= cfg["rain_skip_prob_pct"]:
        return rain_mm_48h * cfg["eff_rain_factor"]
    return 0.0


def irrigation_litres(vwc_now: float, area_acres: float, method: str, thresholds: dict, cfg: dict,
                      eff_rain_mm: float = 0.0) -> dict:
    """Below the trigger, refill toward field capacity, capped per day and per event for the method."""
    if method not in IRRIGATION_METHODS:
        raise ValueError(f"irrigation method must be one of {IRRIGATION_METHODS}, got {method!r}")
    return irrigation_plan(
        vwc_now,
        thresholds["trigger"],
        cfg["root_depth_mm"],
        area_acres,
        cfg[f"efficiency_{method}"],
        cfg["max_daily_mm"],
        cfg[f"max_event_mm_{method}"],
        refill_target=thresholds["fc"],
        eff_rain_mm=eff_rain_mm,
    )
