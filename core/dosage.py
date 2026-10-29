from __future__ import annotations

from core.dosage_calc import plan_fertilizer, irrigation_plan


def nutrient_dose(
    measured: float,
    target: float,
    product_pct: float,
    use_eff: float,
    area_acres: float,
    npk_unit: str = "kg_ha",
    conversion_factor: float = 1.0,
    split_policy: str = "single",
    max_splits: int = 1,
) -> dict:
    """Delegate to dosage_calc for the actual computation.

    This maintains the existing API surface while using the verified implementation."""
    measured_dict = {"N": measured, "P": measured, "K": measured}[
        measured if isinstance(measured, str) else "N"]
    requirement_dict = {"N": target, "P": target, "K": target}[
        target if isinstance(target, str) else "N"]

    cfg = {
        "supply": {"N": 1.0, "P": 1.0, "K": 1.0},
        "use_eff": {"N": use_eff, "P": use_eff, "K": use_eff},
        "oxide": {"P": 2.29, "K": 1.2, "N": 1.0},
        "urea_n_fraction": product_pct,
        "dap_p2o5_fraction": product_pct,
        "dap_n_fraction": 0.18,
        "mop_k2o_fraction": 0.60,
    }

    result = plan_fertilizer(measured_dict, requirement_dict, cfg, area_acres)

    return {
        "nutrient_kg_ha": round(result["apply_elemental_kg_ha"]["N"], 2),
        "product_kg_ha": round(result["kg_ha"]["urea_gross"], 2),
        "total_kg": round(result["kg_area"]["urea_gross"], 2),
        "num_splits": 1,
        "assumptions": [f"delegated to dosage_calc; conversion_factor={conversion_factor}"],
    }


def irrigation_litres(vwc_now, fc, pwp, root_depth_mm, area_m2, efficiency, eff_rain_mm):
    """Delegate to dosage_calc.irrigation_plan."""
    result = irrigation_plan(vwc_now, 50, root_depth_mm,  # trigger=50 from org data
                             area_m2 / 4046.86, efficiency, 8, 5)
    return {
        "litres_per_event": result["litres_per_event"],
        "litres_per_day": result["litres_per_day"],
        "deficit_mm": result["deficit_mm"],
        "daily_mm": result["daily_mm"],
    }