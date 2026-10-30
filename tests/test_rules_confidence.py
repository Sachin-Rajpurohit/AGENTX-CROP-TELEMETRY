from config.agronomy import load_agronomy, moisture_thresholds, stage_for_days
from core.confidence import compute_score
from core.rules import fire_rules

CFG = load_agronomy()


def rules(**overrides):
    args = dict(irrigation_needed=False, rain_mm_48h=0.0, rain_prob_48h=0.0, fertilizer_due=False,
                moisture=55.0, fc=65.0, trigger=50.0, tmax_next3=30.0, cfg=CFG)
    args.update(overrides)
    return fire_rules(**args)


def test_dry_soil_irrigates():
    r = rules(irrigation_needed=True, moisture=30)
    assert r["decision"] == "IRRIGATE"
    assert r["fired_rules"] == ["R9_IRRIGATE"]


def test_dry_soil_with_fertilizer_due_irrigates_first():
    r = rules(irrigation_needed=True, fertilizer_due=True, moisture=30)
    assert r["decision"] == "IRRIGATE_THEN_FERTILIZE"


def test_dry_no_fert_compares_against_trigger_not_fc():
    # 55% is above the trigger (50) but below fc (65): soil is not dry, fertilize directly.
    assert rules(fertilizer_due=True, moisture=55)["decision"] == "FERTILIZE"


def test_rain_skips_irrigation():
    r = rules(irrigation_needed=True, moisture=30, rain_mm_48h=12, rain_prob_48h=80)
    assert r["decision"] == "WAIT_FOR_RAIN"
    assert "R9_IRRIGATE" in r["fired_rules"]


def test_unlikely_rain_does_not_skip_irrigation():
    assert rules(irrigation_needed=True, moisture=30, rain_mm_48h=12, rain_prob_48h=30)["decision"] == "IRRIGATE"


def test_heavy_rain_delays_fertilizer():
    assert rules(fertilizer_due=True, rain_mm_48h=30, rain_prob_48h=90)["decision"] == "DELAY_FERTILIZER"


def test_heat_adds_dawn_timing_when_irrigating():
    r = rules(irrigation_needed=True, moisture=30, tmax_next3=37)
    assert r["decision"] == "IRRIGATE"
    assert "R4_HEAT_DAWN" in r["fired_rules"]


def test_heat_alone_is_not_an_action():
    r = rules(tmax_next3=37)
    assert r["decision"] == "NO_ACTION"
    assert "R4_HEAT_DAWN" not in r["fired_rules"]


def test_saturated_soil():
    assert rules(moisture=70)["decision"] == "DRAINAGE_WARNING"


def test_sensor_fault_overrides_everything():
    r = rules(irrigation_needed=True, fertilizer_due=True, moisture=10, tmax_next3=40, has_sensor_fault=True)
    assert r["decision"] == "INSPECT_SENSOR"
    assert r["fired_rules"] == ["R5_FLATLINE_HOLD"]


def test_no_action_default():
    assert rules()["fired_rules"] == ["R8_NO_ACTION"]


def test_confidence_uses_config_thresholds():
    assert compute_score(CFG) == (1.0, [], "HIGH")
    score, reasons, level = compute_score(CFG, weather_fallback=True, less_than_5_days=True)
    assert score == 0.70 and level == "HIGH" and len(reasons) == 2
    assert compute_score(CFG, has_flatline=True)[2] == "MEDIUM"  # 0.65


def test_confidence_capped_on_sensor_fault():
    score, reasons, level = compute_score(CFG, sensor_fault=True)
    assert score == 0.40 and level == "MEDIUM"
    assert "sensor fault: confidence capped" in reasons


def test_stage_for_days():
    assert [stage_for_days(d) for d in (0, 20, 21, 45, 46, 70, 71, 200)] == [
        "seedling", "seedling", "vegetative", "vegetative", "flowering", "flowering", "fruiting", "fruiting"]


def test_fao56_trigger_per_soil():
    assert moisture_thresholds("clay_loam")["trigger"] == 25.2   # 32 - 0.4 * (32 - 15)
    assert moisture_thresholds("sandy_loam")["trigger"] == 10.4  # 14 - 0.4 * (14 - 5)
    assert moisture_thresholds()["soil"] == "clay_loam"
    assert moisture_thresholds("clay_loam", crop="rice")["trigger"] == 32  # flooded: re-irrigate below FC


def test_flooded_crop_never_gets_drainage_warning():
    assert rules(moisture=70, flooded=True)["decision"] == "NO_ACTION"  # helper fc is 65
    assert rules(moisture=70)["decision"] == "DRAINAGE_WARNING"
