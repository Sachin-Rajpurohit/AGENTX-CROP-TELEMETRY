import json
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.data_query import analyze_soil_telemetry, load_crop_requirements
from tools.web_search import get_weather_forecast
from tools.crop_tools import calculate_fertilizer_water_dosage
from tools.calculator import evaluate_expression

def test_soil_telemetry_analysis():
    """Verify 7-day soil telemetry trend analysis from CSV."""
    obs = analyze_soil_telemetry(plot_id="Trichy Plot #4", days=7)
    assert obs.get("status") == "success", f"Expected success status, got: {obs}"
    assert obs.get("crop") == "tomato", f"Expected crop tomato, got: {obs.get('crop')}"
    assert "current_moisture_pct" in obs, "Missing current_moisture_pct"
    assert "current_npk_kg_ha" in obs, "Missing current_npk_kg_ha"
    assert len(obs["current_npk_kg_ha"]) == 3, "NPK must have 3 components"
    assert obs["soil_ph"] > 0, "pH must be positive"
    assert obs["root_temp_c"] > 0, "Root temp must be positive"
    print("  [PASS] test_soil_telemetry_analysis")

def test_soil_telemetry_missing_plot_fallback():
    """Verify graceful handling when an unknown plot is queried."""
    obs = analyze_soil_telemetry(plot_id="NonExistent_Plot_999", days=7)
    assert "status" in obs, "Result must contain status"
    print("  [PASS] test_soil_telemetry_missing_plot_fallback")

def test_weather_forecast_tool():
    """Verify live/cached weather forecast returns structured precipitation risk."""
    weather = get_weather_forecast(location="Tiruchirappalli", days=3)
    assert "total_rainfall_mm" in weather, "Missing total_rainfall_mm"
    assert "max_rain_probability_pct" in weather, "Missing max_rain_probability_pct"
    assert "heavy_rain_risk" in weather, "Missing heavy_rain_risk"
    assert "should_delay_irrigation" in weather, "Missing should_delay_irrigation"
    assert isinstance(weather["total_rainfall_mm"], (int, float))
    assert 0 <= weather["max_rain_probability_pct"] <= 100
    print("  [PASS] test_weather_forecast_tool")

def test_dosage_calculator_mathematics():
    """
    Verify agronomic conversions:
    - 40 kg/ha deficit / 2.47105 = 16.19 kg/acre pure N -> 35.2 kg commercial Urea (46% N)
    - 0 kg/ha deficit -> 0.0 kg commercial P (SSP/DAP)
    - 20 kg/ha deficit / 2.47105 = 8.09 kg/acre pure K -> 13.5 kg commercial MOP (60% K2O)
    - 7.0 mm depth * 4046.86 L/mm/acre = 28,300 L water/acre
    """
    res = calculate_fertilizer_water_dosage(
        crop="tomato",
        current_moisture_pct=22.0,
        target_moisture_pct=65.0,
        current_npk_kg_ha=[40.0, 20.0, 30.0],
        target_npk_kg_ha=[80.0, 20.0, 50.0],
        field_area_acres=1.0,
        heavy_rain_expected=False
    )
    assert res["status"] == "success"
    fert = res["commercial_fertilizer_kg_per_acre"]
    elem = res["elemental_deficit_kg_per_acre"]
    irrig = res["irrigation_schedule"]

    assert fert["urea_46_pct_N_kg"] == 35.2, f"Expected 35.2 kg Urea, got {fert['urea_46_pct_N_kg']}"
    assert fert["ssp_16_pct_P2O5_kg"] == 0.0, f"Expected 0.0 kg SSP, got {fert['ssp_16_pct_P2O5_kg']}"
    assert fert["mop_60_pct_K2O_kg"] == 13.5, f"Expected 13.5 kg MOP, got {fert['mop_60_pct_K2O_kg']}"
    assert irrig["water_volume_liters_per_acre"] == 28300, f"Expected 28,300 L, got {irrig['water_volume_liters_per_acre']}"
    assert irrig["application_depth_mm"] == 7.0
    print("  [PASS] test_dosage_calculator_mathematics")

def test_dosage_calculator_heavy_rain_interlock():
    """When heavy rain is expected, irrigation volume must be zero and fertilizer withheld."""
    res = calculate_fertilizer_water_dosage(
        crop="tomato",
        current_moisture_pct=20.0,
        target_moisture_pct=65.0,
        current_npk_kg_ha=[30.0, 10.0, 20.0],
        target_npk_kg_ha=[80.0, 20.0, 50.0],
        field_area_acres=1.0,
        heavy_rain_expected=True
    )
    assert res["irrigation_schedule"]["water_volume_liters_per_acre"] == 0
    assert res["irrigation_schedule"]["application_depth_mm"] == 0.0
    print("  [PASS] test_dosage_calculator_heavy_rain_interlock")

def test_dosage_area_scaling():
    """Verify that a 2.5 acre field receives proportionally 2.5x fertilizer and water."""
    res_1 = calculate_fertilizer_water_dosage(crop="tomato", field_area_acres=1.0)
    res_2 = calculate_fertilizer_water_dosage(crop="tomato", field_area_acres=2.5)
    urea_1 = res_1["commercial_fertilizer_kg_per_acre"]["urea_46_pct_N_kg"]
    urea_2 = res_2["commercial_fertilizer_kg_per_acre"]["urea_46_pct_N_kg"]
    assert abs(urea_2 - (urea_1 * 2.5)) < 0.5, f"Expected ~{urea_1 * 2.5}, got {urea_2}"
    print("  [PASS] test_dosage_area_scaling")

def test_crop_requirements_database():
    """Verify grounded TNAU/ICAR crop requirements lookup."""
    tomato_req = load_crop_requirements("tomato")
    paddy_req = load_crop_requirements("paddy")
    rice_req = load_crop_requirements("rice")
    assert tomato_req["target_moisture_pct"] == 65.0
    assert paddy_req["target_moisture_pct"] == 35.0
    assert rice_req["target_moisture_pct"] == 35.0
    assert paddy_req["target_npk_kg_ha"] == [100.0, 50.0, 50.0]
    print("  [PASS] test_crop_requirements_database")

def test_safe_calculator():
    """Verify safe mathematical evaluator."""
    val = evaluate_expression("40 / 2.47105 / 0.46")
    assert val["status"] == "success"
    assert abs(float(val["result"]) - 35.18) < 0.1
    print("  [PASS] test_safe_calculator")

def run_all():
    print("Running Suite: tests/test_tools.py...")
    test_soil_telemetry_analysis()
    test_soil_telemetry_missing_plot_fallback()
    test_weather_forecast_tool()
    test_dosage_calculator_mathematics()
    test_dosage_calculator_heavy_rain_interlock()
    test_dosage_area_scaling()
    test_crop_requirements_database()
    test_safe_calculator()
    print("All tool tests passed successfully!\n")

if __name__ == "__main__":
    run_all()
