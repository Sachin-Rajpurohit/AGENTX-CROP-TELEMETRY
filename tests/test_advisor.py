import re

import pandas as pd
import pytest

from agent.advisor import run_advisory
from config import DATA_DIR
from core.schema import WeatherRisk

DRY = WeatherRisk(rain_mm_48h=0.0, rain_prob_48h=10.0, tmax_next3=33.0, source="live")
RAINY = WeatherRisk(rain_mm_48h=15.0, rain_prob_48h=85.0, tmax_next3=30.0, source="live")
SAMPLE = pd.read_csv(f"{DATA_DIR}/soil_telemetry.csv")


def advise(df=SAMPLE, weather=DRY, **kw):
    args = dict(area_acres=1.0, irrigation="drip", days_after_transplanting=60, lat=10.79, lon=78.70)
    args.update(kw)
    return run_advisory(df, weather=weather, **args)


def test_sample_matches_hand_computation():
    r = advise()  # 60 days -> flowering: N100 P50 K60, measured N40 P20 K30, moisture 22%
    assert r["stage"] == "flowering"
    assert r["decision"] == "IRRIGATE_THEN_FERTILIZE"
    kg = r["doses"]["fertilizer"]["kg_area"]
    assert kg["urea_gross"] == pytest.approx(87.98, abs=0.02)
    assert kg["urea_net"] == pytest.approx(40.67, abs=0.02)
    assert kg["dap"] == pytest.approx(120.88, abs=0.02)
    assert kg["mop"] == pytest.approx(34.69, abs=0.02)
    assert r["doses"]["irrigation"]["litres_per_day"] == pytest.approx(35972.09, rel=1e-4)


def test_sample_uses_fao56_clay_loam_trigger():
    r = advise()  # clay loam FC 32, PWP 15, p 0.40 -> trigger 25.2; sample dries 31 -> 22
    assert r["moisture_thresholds"] == {"crop": "tomato", "soil": "clay_loam", "fc": 32, "pwp": 15, "trigger": 25.2}
    irr = r["doses"]["irrigation"]
    assert irr["deficit_mm"] == pytest.approx(30.0)  # (32 - 22)% of 300 mm root zone, refilled to FC
    assert irr["daily_mm"] == 8 and irr["days_to_refill"] == 4
    assert r["confidence"] == {"score": 1.0, "level": "HIGH", "reasons": []}


def test_moist_soil_above_trigger_needs_no_water():
    r = advise(df=SAMPLE.assign(moisture=[31, 30, 30, 29, 29, 28, 28, 27]))
    assert r["decision"] == "FERTILIZE"
    assert r["doses"]["irrigation"]["irrigate"] is False


def test_soil_type_changes_trigger():
    r = advise(soil="sandy_loam")  # FC 14: 22% is above field capacity
    assert r["decision"] == "DRAINAGE_WARNING"


def test_advisory_text_carries_numbers_and_disclaimer():
    r = advise()
    assert "35,972 litres" in r["advisory"]["en"]
    assert "Urea 40.7 kg" in r["advisory"]["en"]
    assert r["advisory"]["en"].endswith("Confirm with a local agriculture officer.")
    ta = r["advisory"]["ta"]
    assert "யூரியா 40.7 கிலோ" in ta and "35,972 லிட்டர்" in ta
    assert not re.search(r"[A-Za-z]{3,}", ta.replace("HIGH", "")), "Tamil text should not contain stray English"


def test_rain_forecast_waits():
    r = advise(weather=RAINY)
    assert r["decision"] == "WAIT_FOR_RAIN"
    assert "litres" not in r["advisory"]["en"]


def test_heat_moves_irrigation_to_dawn():
    r = advise(df=SAMPLE.assign(N=200, P=200, K=200),
               weather=WeatherRisk(rain_mm_48h=0, rain_prob_48h=0, tmax_next3=38, source="live"))
    assert r["decision"] == "IRRIGATE"
    assert "before 07:00" in r["advisory"]["en"]


def test_flatlined_moisture_sensor_gives_no_doses():
    r = advise(df=SAMPLE.assign(moisture=30))
    assert r["decision"] == "INSPECT_SENSOR"
    assert r["doses"] is None
    assert r["confidence"]["score"] <= 0.40


def test_fallback_weather_lowers_confidence():
    r = advise(weather=WeatherRisk(rain_mm_48h=0, rain_prob_48h=10, tmax_next3=33, source="fallback"))
    assert r["confidence"]["score"] == 0.85


def test_missing_npk_skips_fertilizer():
    r = advise(df=SAMPLE.drop(columns=["N", "P", "K"]))
    assert r["decision"] == "IRRIGATE"
    assert r["doses"]["fertilizer"] is None
    assert "missing NPK readings" in r["confidence"]["reasons"]


def test_single_manual_reading_works():
    # Seedling needs N40 P50 K30: every nutrient is above requirement, moisture between trigger and fc.
    r = advise(df=pd.DataFrame([{"moisture": 28, "N": 90, "P": 55, "K": 55}]), days_after_transplanting=10)
    assert r["stage"] == "seedling"
    assert r["decision"] == "NO_ACTION"
    assert "< 5 days of data" in r["confidence"]["reasons"]


def test_flood_uses_lower_efficiency():
    drip = advise()["doses"]["irrigation"]["litres_per_day"]
    flood = advise(irrigation="flood")["doses"]["irrigation"]["litres_per_day"]
    assert flood == pytest.approx(drip * 0.90 / 0.60, rel=1e-3)


def test_crop_comes_from_csv_column():
    assert advise()["crop"] == "tomato"  # soil_telemetry.csv has crop=tomato
    assert advise(df=SAMPLE.assign(crop="paddy"))["crop"] == "rice"


def test_maize_and_cotton_use_their_own_fao56_p():
    maize, cotton = advise(crop="maize"), advise(crop="cotton")
    assert maize["moisture_thresholds"]["trigger"] == 22.65   # 32 - 0.55 * 17
    assert cotton["moisture_thresholds"]["trigger"] == 20.95  # 32 - 0.65 * 17
    assert maize["stage"] == cotton["stage"] == "whole_season"
    assert maize["decision"] == "IRRIGATE_THEN_FERTILIZE"   # 22% < 22.65%
    assert cotton["decision"] == "FERTILIZE"                # 22% > 20.95%: cotton tolerates drier soil
    assert maize["doses"]["fertilizer"]["deficit_kg_ha"] == {"N": 80, "P": 40, "K": 20}  # N120 P60 K50 target


def test_rice_is_flooded_not_dripped():
    r = advise(crop="rice", days_after_transplanting=30)
    assert r["stage"] == "tillering"
    assert r["doses"]["method"] == "flood"
    irr = r["doses"]["irrigation"]
    assert irr["daily_mm"] == 50 and irr["events_per_day"] == 1           # TNAU: flood to 5 cm
    assert irr["litres_per_day"] == pytest.approx(50 / 0.60 * 4046.86, rel=1e-4)
    assert "re-flood" in r["advisory"]["en"] and "நெல்" in r["advisory"]["ta"]


def test_ponded_rice_is_not_a_sensor_fault_or_drainage_problem():
    r = advise(df=SAMPLE.assign(moisture=40), crop="rice")
    assert r["decision"] != "INSPECT_SENSOR" and r["decision"] != "DRAINAGE_WARNING"
    assert r["doses"]["irrigation"]["irrigate"] is False


def test_crop_fit_reported():
    fit = advise()["crop_fit"]
    assert fit["available"] and len(fit["best_matches"]) == 3
    assert fit["selected_crop_in_dataset"] is False  # tomato is not in the Kaggle dataset


@pytest.mark.parametrize("df, kw, msg", [
    (SAMPLE.drop(columns=["moisture"]), {}, "moisture"),
    (SAMPLE, {"area_acres": 0}, "area_acres"),
    (SAMPLE, {"irrigation": "sprinkler"}, "irrigation method"),
    (SAMPLE, {"soil": "peat"}, "soil must be one of"),
    (SAMPLE, {"crop": "banana"}, "crop must be one of"),
    (SAMPLE, {"crop": "maize", "stage": "flowering"}, None),  # stage ignored for whole-season crops
    (SAMPLE, {"crop": "rice", "stage": "fruiting"}, "stage for rice must be one of"),
])
def test_input_validation(df, kw, msg):
    if msg is None:
        advise(df=df, **kw)
        return
    with pytest.raises(ValueError, match=msg):
        advise(df=df, **kw)
