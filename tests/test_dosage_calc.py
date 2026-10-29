import pytest
from core.dosage_calc import plan_fertilizer, irrigation_plan

CFG = {
    "supply": {"N": 1.0, "P": 1.0, "K": 1.0},
    "use_eff": {"N": 0.6, "P": 0.5, "K": 0.7},
    "oxide": {"P": 2.29, "K": 1.2},
    "urea_n_fraction": 0.46, "dap_p2o5_fraction": 0.46,
    "dap_n_fraction": 0.18, "mop_k2o_fraction": 0.60,
}
MEAS = {"N": 40, "P": 20, "K": 30}
REQ = {"N": 100, "P": 50, "K": 60}


def test_gross_urea():
    r = plan_fertilizer(MEAS, REQ, CFG, 1.0)
    assert r["kg_ha"]["urea_gross"] == pytest.approx(217.39, abs=0.02)
    assert r["kg_area"]["urea_gross"] == pytest.approx(87.975, abs=0.02)


def test_dap_uses_p2o5_conversion():
    r = plan_fertilizer(MEAS, REQ, CFG, 1.0)
    assert r["apply_elemental_kg_ha"]["P"] == pytest.approx(60.0)
    assert r["oxide_kg_ha"]["P2O5"] == pytest.approx(137.4)
    assert r["kg_ha"]["dap"] == pytest.approx(298.70, abs=0.02)
    assert r["kg_area"]["dap"] == pytest.approx(120.88, abs=0.02)


def test_dap_n_credit_and_net_urea():
    r = plan_fertilizer(MEAS, REQ, CFG, 1.0)
    assert r["kg_ha"]["dap_n_credit_kg_n"] == pytest.approx(53.77, abs=0.02)
    assert r["kg_ha"]["urea_net"] == pytest.approx(100.51, abs=0.02)
    assert r["kg_area"]["urea_net"] == pytest.approx(40.675, abs=0.02)


def test_mop():
    r = plan_fertilizer(MEAS, REQ, CFG, 1.0)
    assert r["kg_ha"]["mop"] == pytest.approx(85.71, abs=0.02)
    assert r["kg_area"]["mop"] == pytest.approx(34.69, abs=0.02)


def test_no_negative_doses_when_soil_is_rich():
    r = plan_fertilizer({"N": 150, "P": 80, "K": 90}, REQ, CFG, 1.0)
    assert all(v == 0 for v in r["kg_ha"].values())


def test_irrigation_capped_and_realistic():
    r = irrigation_plan(22, 50, 300, 1.0, 0.9, 8, 5)
    assert r["deficit_mm"] == pytest.approx(84.0)
    assert r["daily_mm"] == 8 and r["clipped"] is True
    assert r["events_per_day"] == 2
    assert r["litres_per_day"] == pytest.approx(35972.09, rel=1e-4)
    assert 10_000 <= r["litres_per_day"] <= 40_000
    assert r["days_to_refill"] == 11


def test_no_irrigation_when_wet():
    assert irrigation_plan(60, 50, 300, 1.0, 0.9, 8, 5)["irrigate"] is False