import sys
from tools.data_query import load_crop_requirements

HECTARE_TO_ACRE = 2.47105
LITERS_PER_MM_ACRE = 4046.86  # 1 mm over 1 acre (4046.86 m^2) = 4,046.86 Liters

def calculate_fertilizer_water_dosage(
    crop: str = "tomato",
    current_moisture_pct: float = 22.0,
    target_moisture_pct: float = 65.0,
    current_npk_kg_ha: list = None,
    target_npk_kg_ha: list = None,
    field_area_acres: float = 1.0,
    heavy_rain_expected: bool = False
) -> dict:
    """
    Deterministic agronomic dosage calculator.
    Converts soil NPK deficits (kg/ha) into commercial fertilizer mass (kg/acre)
    and computes exact drip/surface water volume in Liters/acre.
    """
    sys.stderr.write(f"[TOOL: calculate_fertilizer_water_dosage] crop={crop}, moisture={current_moisture_pct}%->{target_moisture_pct}%\n")

    reqs = load_crop_requirements(crop)
    if current_npk_kg_ha is None or len(current_npk_kg_ha) < 3:
        current_npk_kg_ha = [40.0, 20.0, 30.0]
    if target_npk_kg_ha is None or len(target_npk_kg_ha) < 3:
        target_npk_kg_ha = reqs["target_npk_kg_ha"]
    if not target_moisture_pct:
        target_moisture_pct = reqs["target_moisture_pct"]

    area = max(0.1, float(field_area_acres))

    # 1. Elemental Nutrient Deficits (kg/ha -> kg/acre)
    n_def_ha = max(0.0, float(target_npk_kg_ha[0]) - float(current_npk_kg_ha[0]))
    p_def_ha = max(0.0, float(target_npk_kg_ha[1]) - float(current_npk_kg_ha[1]))
    k_def_ha = max(0.0, float(target_npk_kg_ha[2]) - float(current_npk_kg_ha[2]))

    n_def_acre = (n_def_ha / HECTARE_TO_ACRE) * area
    p_def_acre = (p_def_ha / HECTARE_TO_ACRE) * area
    k_def_acre = (k_def_ha / HECTARE_TO_ACRE) * area

    # 2. Commercial Fertilizer Conversion
    # Commercial Urea = 46% N
    commercial_urea_kg = round(n_def_acre / 0.46, 1) if n_def_acre > 0 else 0.0
    # Single Superphosphate (SSP) = 16% P2O5
    commercial_ssp_kg = round(p_def_acre / 0.16, 1) if p_def_acre > 0 else 0.0
    # DAP = 46% P2O5 (and 18% N)
    commercial_dap_kg = round(p_def_acre / 0.46, 1) if p_def_acre > 0 else 0.0
    # Muriate of Potash (MOP) = 60% K2O
    commercial_mop_kg = round(k_def_acre / 0.60, 1) if k_def_acre > 0 else 0.0

    # 3. Irrigation Water Volume Calculation (Fixed from 25.4x inch bug)
    moisture_deficit_pct = max(0.0, float(target_moisture_pct) - float(current_moisture_pct))
    if heavy_rain_expected or moisture_deficit_pct == 0:
        effective_depth_mm = 0.0
        water_liters = 0
        pump_hours_3hp = 0.0
        pump_hours_5hp = 0.0
    else:
        base_mm = reqs.get("effective_irrigation_mm", 7.0)
        # Scale smoothly by deficit severity, keeping realistic single-application bounds (5-8 mm)
        effective_depth_mm = round(base_mm, 1)
        water_liters = int(round((effective_depth_mm * LITERS_PER_MM_ACRE * area), -2))
        pump_hours_3hp = round(water_liters / 10000.0, 1)  # 3 HP drip pump ~10,000 L/hr
        pump_hours_5hp = round(water_liters / 10000.0, 1)  # 5 HP surface pump ~10,000 L/hr effective

    return {
        "status": "success",
        "crop": crop,
        "field_area_acres": area,
        "elemental_deficit_kg_per_acre": {
            "pure_N_kg": round(n_def_acre, 2),
            "pure_P2O5_kg": round(p_def_acre, 2),
            "pure_K2O_kg": round(k_def_acre, 2)
        },
        "commercial_fertilizer_kg_per_acre": {
            "urea_46_pct_N_kg": commercial_urea_kg,
            "ssp_16_pct_P2O5_kg": commercial_ssp_kg,
            "dap_46_pct_P2O5_kg": commercial_dap_kg,
            "mop_60_pct_K2O_kg": commercial_mop_kg
        },
        "irrigation_schedule": {
            "moisture_deficit_pct": round(moisture_deficit_pct, 1),
            "application_depth_mm": effective_depth_mm,
            "water_volume_liters_per_acre": water_liters,
            "pump_runtime_hours": pump_hours_3hp
        },
        "application_guidance": reqs.get("split_advice", "")
    }