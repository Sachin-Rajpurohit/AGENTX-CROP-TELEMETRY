from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.quality import check_quality
from core.trends import analyze_trends
from core.weather import get_weather_risk
from core.dosage import nutrient_dose, irrigation_litres
from core.rules import fire_rules
from core.confidence import compute_score, confidence_level

from config.agronomy import (
    NPK_UNIT, FC, PWP, TRIGGER_MOISTURE_PCT,
    USE_EFF, OXIDE_FACTORS, PRODUCT_FRACTIONS,
    HEAT_THRESHOLD_C,
)


@dataclass
class AdvisoryResult:
    decision: str
    confidence: dict
    advisory: dict
    doses: dict
    calendar: list
    impact: dict
    rules_fired: list[str]
    assumptions: list[str]
    trace: list[dict]


def _format_number(n: float) -> str:
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}"


def _advisory_text(result: AdvisoryResult, language: str = "en") -> str:
    d = result.decision
    c = result.confidence
    reasons = c["reasons"]
    a = result.doses

    if language == "ta":
        parts = [
            f"மூட்டு நிலை: {_format_number(a.get('moisture', 0))}",
            f"த Pietrainம்: {d}",
            f"நம்பிக்கை: {c['level']} ({_format_number(c['score'] * 100)}%)",
        ]
        if reasons:
            parts.append(f"உasons: {', '.join(reasons)}")
        parts.append(f"ச{{_format_number(a.get('litres_per_day', 0))}} Liter/-acre/วัน")
        return " ".join(parts)
    else:
        parts = [
            f"Decision: {d}",
            f"Confidence: {c['level']} ({_format_number(c['score'] * 100)}%)",
        ]
        if reasons:
            parts.append(f"Reasons: {', '.join(reasons)}")
        if "litres_per_day" in a:
            parts.append(f"Recommended irrigation: {_format_number(a['litres_per_day'])} L/acre/day")
        if "urea_gross" in a:
            parts.append(
                f"Fertilizer: Urea {_format_number(a.get('urea_gross', 0))} kg/ha, "
                f"DAP {_format_number(a.get('dap', 0))} kg/ha, "
                f"MOP {_format_number(a.get('mop', 0))} kg/ha"
            )
        return ". ".join(parts) + "."


def _run_deterministic_pipeline(
    df,
    area_acres: float,
    irrigation: str,
    days_after_transplanting: int,
    lat: float,
    lon: float,
) -> AdvisoryResult:
    start = time.time()

    # 1. Quality
    qr = check_quality(df)
    trace = [{"step": "quality", "tool": "check_quality", "observation": qr.model_dump()}]

    # 2. Trends
    tr = analyze_trends(df, {})
    trace.append({"step": "trends", "tool": "analyze_trends", "observation": tr.model_dump()})

    # 3. Weather
    weather = get_weather_risk(lat, lon, days=5)
    trace.append({"step": "weather", "tool": "get_weather_risk", "observation": weather.model_dump()})

    # 4. Rules
    moisture = df["moisture"].iloc[-1] if len(df) > 0 else 0
    has_sensor_fault = any(i.code in ("FLATLINE", "OUT_OF_RANGE") for i in qr.issues)
    rules_result = fire_rules(
        irrigation_needed=trends["days_to_trigger"] is not None,
        rain_mm_48h=weather.rain_mm_48h,
        rain_prob_48h=weather.rain_prob_48h,
        fertilizer_due=trends["npk_slope_per_day"].N < 0
        or trends["npk_slope_per_day"].P < 0
        or trends["npk_slope_per_day"].K < 0,
        moisture=moisture,
        fc=FC,
        tmax_next3=weather.tmax_next3,
        has_sensor_fault=has_sensor_fault,
        computed_doses_exceed_cap=False,
    )
    trace.append({"step": "rules", "tool": "fire_rules", "observation": rules_result})

    # 5. Dosage
    measured = {
        "N": df["N"].iloc[-1],
        "P": df["P"].iloc[-1],
        "K": df["K"].iloc[-1],
    }
    requirement = {"N": 100, "P": 50, "K": 60}
    dos = nutrient_dose(
        measured=measured,
        target=requirement,
        product_pct=0.46,
        use_eff=USE_EFF,
        area_acres=area_acres,
    )
    trace.append({"step": "dosage", "tool": "nutrient_dose", "observation": dos})

    # 6. Irrigation
    vwc_now = df["moisture"].iloc[-1] if len(df) > 0 else 0
    irr = irrigation_litres(
        vwc_now=vwc_now,
        fc=FC,
        pwp=PWP,
        root_depth_mm=300,
        area_m2=area_acres * 4046.86,
        efficiency=0.90 if irrigation == "drip" else 0.60,
        eff_rain_mm=weather.rain_mm_48h * 0.8 if weather.rain_prob_48h >= 60 else 0.0,
    )
    trace.append({"step": "irrigation", "tool": "irrigation_litres", "observation": irr.model_dump()})

    # 7. Confidence
    score, reasons, level = compute_score(
        has_flatline=has_sensor_fault,
        has_gap=len(qr.issues) > 0,
        weather_fallback=weather.source == "fallback",
        missing_npk=any(c not in df.columns for c in ["N", "P", "K"]),
        less_than_5_days=len(df) < 5,
    )
    trace.append({
        "step": "confidence",
        "tool": "compute_score",
        "observation": {"score": score, "reasons": reasons, "level": level},
    })

    advisory_text_en = _advisory_text(__import__("__main__", fromlist=[""]).AdvisoryResult, "en")
    advisory_text_ta = _advisory_text(__import__("__main__", fromlist=[""]).AdvisoryResult, "ta")

    return AdvisoryResult(
        decision=rules_result["decision"],
        confidence={"level": level, "score": score, "reasons": reasons},
        advisory={"en": advisory_text_en, "ta": advisory_text_ta},
        doses=dos,
        calendar=[],
        impact={},
        rules_fired=rules_result["fired_rules"],
        assumptions=[
            f"trigger={TRIGGER_MOISTURE_PCT} (from org data: minTomatoMoisture)",
            f"fc={FC}%, pwp={PWP}% (ASSUMPTION)",
            f"npk_unit={NPK_UNIT}",
        ],
        trace=trace,
    )
