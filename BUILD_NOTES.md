# BUILD NOTES for AGENTX Crop Telemetry Sensor-to-Dose Advisor
# Updated: 29 October 2026

## Moisture Scale Conversion
- moisturePercentage < 50 ⇒ pump ON; (14 of 14 ON rows below 50, 379 of 379 OFF rows above 51)
- High raw ADC value = dry soil; low raw ADC value = wet soil (scales may differ between JSON and soil_telemetry.csv)
- minTomatoMoisture from JSON = 50 (used as irrigation trigger)
- soil_telemetry.csv range (22-31) sits outside JSON's (38-68) → keep confidence deduction for scale mismatch

## Config Updates (config/agronomy.yaml)
- trigger_moisture_pct: 50 (FROM org data: minTomatoMoisture)
- fc_moisture_pct: 65 (ASSUMPTION)
- pwp_moisture_pct: 40 (ASSUMPTION)
- NPK units: kg_ha (fertilizer requirements, no 1.95 bulk-density conversion)

## Dosage Logic Changes (core/dosage.py)
- Product kg = nutrient kg x oxide factor / product fraction
- P: product_kg_ha = nutrient_to_apply * p_to_p2o5 / dap_pct (includes ×2.29 P2O5 factor)
- K: product_kg_ha = nutrient_to_apply * k_to_k2o / mop_k2o_pct (includes ×1.20 K2O factor)
- DAP N-credit computed from same DAP amount: DAP_N_credit = DAP_kg_ha * dap_n_pct
- Net urea = (target_N - DAP_N_credit) / product_pct_N (in urea kg, not N kg)

## Dosage Hand-Computed Values (1 acre, flowering stage)
- Targets: N100 P50 K60 kg/ha (fertilizer requirements)
- Measured: N40 P20 K30 (on 0-100 index)
- use_eff: N0.6 P0.5 K0.7
- Gross urea: 217.39 kg/ha = 87.98 kg/acre
- DAP: 298.70 kg/ha = 120.88 kg/acre
- DAP N-credit: 53.77 kg N/ha = 21.76 kg N/acre
- Net urea: 100.51 kg/ha = 40.67 kg/acre
- MOP: 85.71 kg/ha = 34.69 kg/acre
- Irrigation: 35,972 L/acre/day (clipped to max_daily_mm=8mm)

## Growth Stage
- Default: "vegetative" (days_after_transplanting ~ 30-45)
- Stages: seedling, vegetative, flowering, fruiting
- Targets per stage from crop_requirements.json

## Test Expectations (tests/test_dosage.py)
- gross urea = 217.39 kg/ha = 87.98 kg/acre
- DAP = 298.70 kg/ha = 120.88 kg/acre
- DAP N credit = 53.77 kg N/ha = 21.76 kg N/acre
- net urea = 100.51 kg/ha = 40.67 kg/acre
- MOP = 85.71 kg/ha = 34.69 kg/acre
- irrigation litres/acre/day between 10,000 and 40,000
- Tests must fail on current code, pass after fix