from __future__ import annotations

from core.rules import fire_rules
from core.confidence import compute_score
from core.dosage import nutrient_dose, irrigation_litres
from core.trends import analyze_trends
from core.weather import get_weather_risk
from core.quality import check_quality


def tool_quality(df) -> dict:
    import pandas as pd
    df = pd.DataFrame(df)
    qr = check_quality(df)
    return {
        "score": qr.score,
        "issues": [{"code": i.code, "severity": i.severity, "detail": i.detail} for i in qr.issues],
    }


def tool_trends(df: dict, cfg: dict) -> dict:
    import pandas as pd
    df = pd.DataFrame(df)
    tr = analyze_trends(df, cfg)
    return {
        "days_to_trigger": tr.days_to_trigger,
        "npk_slope_per_day": {
            "N": tr.npk_slope_per_day.N,
            "P": tr.npk_slope_per_day.P,
            "K": tr.npk_slope_per_day.K,
        },
        "heat_stress_hours": tr.heat_stress_hours,
    }


def tool_weather(lat: float, lon: float, days: int = 5) -> dict:
    from core.weather import WeatherRisk
    wr = get_weather_risk(lat, lon, days=days)
    return {
        "rain_mm_48h": wr.rain_mm_48h,
        "rain_prob_48h": wr.rain_prob_48h,
        "tmax_next3": wr.tmax_next3,
        "source": wr.source,
    }


def tool_dosage(measured: dict, target: dict, area_acres: float,
                product_pct: float, use_eff: float) -> dict:
    dos = nutrient_dose(
        measured=measured,
        target=target,
        product_pct=product_pct,
        use_eff=use_eff,
        area_acres=area_acres,
    )
    return {
        "deficit_kg_ha": dos["deficit_kg_ha"],
        "apply_elemental_kg_ha": dos["apply_elemental_kg_ha"],
        "oxide_kg_ha": dos["oxide_kg_ha"],
        "kg_ha": dos["kg_ha"],
        "kg_area": dos["kg_area"],
        "num_splits": dos["num_splits"],
        "assumptions": dos["assumptions"],
    }


def tool_irrigation(vwc_now: float, fc: float, pwp: float,
                    root_depth_mm: float, area_m2: float,
                    efficiency: float, eff_rain_mm: float) -> dict:
    irr = irrigation_litres(
        vwc_now=vwc_now,
        fc=fc,
        pwp=pwp,
        root_depth_mm=root_depth_mm,
        area_m2=area_m2,
        efficiency=efficiency,
        eff_rain_mm=eff_rain_mm,
    )
    return {
        "litres_per_event": irr["litres_per_event"],
        "litres_per_day": irr["litres_per_day"],
        "deficit_mm": irr["deficit_mm"],
        "daily_mm": irr["daily_mm"],
    }


def tool_rules(
    irrigation_needed: bool,
    rain_mm_48h: float,
    rain_prob_48h: float,
    fertilizer_due: bool,
    moisture: float,
    fc: float,
    tmax_next3: float,
    has_sensor_fault: bool = False,
    computed_doses_exceed_cap: bool = False,
) -> dict:
    result = fire_rules(
        irrigation_needed=irrigation_needed,
        rain_mm_48h=rain_mm_48h,
        rain_prob_48h=rain_prob_48h,
        fertilizer_due=fertilizer_due,
        moisture=moisture,
        fc=fc,
        tmax_next3=tmax_next3,
        has_sensor_fault=has_sensor_fault,
        computed_doses_exceed_cap=computed_doses_exceed_cap,
    )
    return {
        "decision": result["decision"],
        "fired_rules": result["fired_rules"],
        "reasons": result["reasons"],
    }


def tool_confidence(has_flatline: bool = False, has_gap: bool = False,
                    has_spike: bool = False, weather_fallback: bool = False,
                    missing_npk: bool = False, less_than_5_days: bool = False) -> dict:
    score, reasons, level = compute_score(
        has_flatline=has_flatline,
        has_gap=has_gap,
        has_spike=has_spike,
        weather_fallback=weather_fallback,
        missing_npk=missing_npk,
        less_than_5_days=less_than_5_days,
    )
    return {"score": score, "reasons": reasons, "level": level}
