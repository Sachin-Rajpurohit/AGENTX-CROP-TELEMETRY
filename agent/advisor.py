"""Deterministic sensor-to-dose pipeline (no LLM).

quality -> trends -> weather -> fertilizer + irrigation doses -> rules -> confidence -> advisory text.
Every constant comes from config/agronomy.yaml.
"""
from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from config.agronomy import (
    WHOLE_SEASON,
    crop_names,
    load_agronomy,
    moisture_thresholds,
    resolve_crop,
    stage_requirement,
    targets_from_dataset,
)
from core.confidence import compute_score
from core.crop_fit import crop_fit
from core.dosage import (
    effective_rain_mm,
    flood_litres,
    irrigation_litres,
    nutrient_dose,
)
from core.quality import _resolve_column, check_quality
from core.rules import fire_rules
from core.schema import WeatherRisk
from core.trends import analyze_trends
from core.weather import get_weather_risk

DISCLAIMER_EN = "Estimate only. Confirm with a local agriculture officer."
DISCLAIMER_TA = "இது மதிப்பீடு மட்டுமே. உள்ளூர் வேளாண் அலுவலரிடம் உறுதிப்படுத்தவும்."

DECISION_TEXT = {
    "INSPECT_SENSOR": (
        "Sensor readings look faulty. Inspect the moisture sensor before acting; no doses are given.",
        "சென்சார் அளவீடுகள் தவறாகத் தெரிகின்றன. செயல்படும் முன் ஈரப்பதம் சென்சாரைச் சரிபார்க்கவும்; அளவு பரிந்துரை இல்லை.",
    ),
    "DRAINAGE_WARNING": (
        "Soil is too wet. Do not irrigate; check field drainage.",
        "மண் அதிக ஈரமாக உள்ளது. நீர் பாய்ச்ச வேண்டாம்; வயலின் வடிகாலைச் சரிபார்க்கவும்.",
    ),
    "WAIT_FOR_RAIN": (
        "Rain is likely within 48 hours. Skip irrigation and recheck after the rain.",
        "48 மணி நேரத்தில் மழை வர வாய்ப்புள்ளது. நீர் பாய்ச்சுவதைத் தவிர்த்து, மழைக்குப் பின் மீண்டும் சரிபார்க்கவும்.",
    ),
    "DELAY_FERTILIZER": (
        "Heavy rain is expected. Delay fertilizer to avoid it washing away.",
        "கனமழை எதிர்பார்க்கப்படுகிறது. உரம் அடித்துச் செல்லப்படாமல் இருக்க உரமிடுவதைத் தள்ளிப்போடவும்.",
    ),
    "IRRIGATE_THEN_FERTILIZE": (
        "Soil is dry. Irrigate first, then apply fertilizer once the soil is moist.",
        "மண் வறண்டுள்ளது. முதலில் நீர் பாய்ச்சி, மண் ஈரமான பிறகு உரமிடவும்.",
    ),
    "IRRIGATE": (
        "Soil is dry. Irrigate today.",
        "மண் வறண்டுள்ளது. இன்று நீர் பாய்ச்சவும்.",
    ),
    "FERTILIZE": (
        "Nutrients are below what the crop needs at this stage. Apply fertilizer.",
        "இந்த வளர்ச்சி நிலைக்குத் தேவையான சத்துகள் குறைவாக உள்ளன. உரமிடவும்.",
    ),
    "NO_ACTION": (
        "No action needed right now.",
        "இப்போது எந்த நடவடிக்கையும் தேவையில்லை.",
    ),
}
# RED = act today, YELLOW = act within 2-3 days, GREEN = no action (judges' answer format)
URGENCY = {
    "INSPECT_SENSOR": "RED", "DRAINAGE_WARNING": "RED", "IRRIGATE_THEN_FERTILIZE": "RED", "IRRIGATE": "RED",
    "WAIT_FOR_RAIN": "YELLOW", "DELAY_FERTILIZER": "YELLOW", "FERTILIZE": "YELLOW", "NO_ACTION": "GREEN",
}
STAGE_NAMES_TA = {"seedling": "நாற்று", "vegetative": "வளர்ச்சி", "flowering": "பூக்கும்", "fruiting": "காய்க்கும்",
                  "tillering": "தூர்கட்டும்", "ripening": "முதிர்ச்சி", WHOLE_SEASON: "முழுப்"}
WATER_DECISIONS = {"IRRIGATE", "IRRIGATE_THEN_FERTILIZE"}
FERTILIZER_DECISIONS = {"FERTILIZE", "IRRIGATE_THEN_FERTILIZE"}


def _latest(df: pd.DataFrame, standard: str) -> float | None:
    col = _resolve_column(df, standard)
    if col is None:
        return None
    vals = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(vals.iloc[-1]) if len(vals) else None


def _csv_crop(df: pd.DataFrame) -> str | None:
    """Crop named in the telemetry itself (a `crop` or `label` column), if any."""
    for col in df.columns:
        if col.lower() in ("crop", "label"):
            vals = df[col].dropna().astype(str)
            return vals.iloc[-1] if len(vals) else None
    return None


def _days_of_data(df: pd.DataFrame) -> int:
    ts_col = _resolve_column(df, "timestamp")
    if ts_col is None:
        return len(df)
    return int(pd.to_datetime(df[ts_col], errors="coerce").dropna().dt.normalize().nunique())


def _fmt(n: float, digits: int = 1) -> str:
    return f"{n:,.0f}" if float(n).is_integer() or digits == 0 else f"{n:,.{digits}f}"


def _advisory(decision: str, crop: str, stage: str, flooded: bool, moisture: float, trigger: float,
              area_acres: float, method: str, doses: dict | None, dawn: bool, confidence: dict) -> dict:
    en, ta = [DECISION_TEXT[decision][0]], [DECISION_TEXT[decision][1]]
    crop_en, crop_ta = crop_names(crop)
    stage_en = "whole-season targets" if stage == WHOLE_SEASON else f"{stage} stage"
    en.append(f"Crop: {crop_en}, {stage_en}.")
    ta.append(f"பயிர்: {crop_ta}, {STAGE_NAMES_TA[stage]} பருவம்.")
    if flooded:
        en.append(f"Soil moisture {_fmt(moisture)}% (re-flood once ponded water is gone, below {_fmt(trigger)}%).")
        ta.append(f"மண் ஈரப்பதம் {_fmt(moisture)}% (தேங்கிய நீர் வடிந்து {_fmt(trigger)}%-க்குக் கீழ் சென்றதும் "
                  f"மீண்டும் நீர் கட்டவும்).")
    else:
        en.append(f"Soil moisture {_fmt(moisture)}% (irrigate below {_fmt(trigger)}%).")
        ta.append(f"மண் ஈரப்பதம் {_fmt(moisture)}% (இது {_fmt(trigger)}%-க்குக் கீழ் சென்றால் நீர் பாய்ச்சவும்).")
    area = f"{_fmt(area_acres)} acre" + ("" if area_acres == 1 else "s")

    if doses and decision in WATER_DECISIONS:
        litres = _fmt(doses["irrigation"]["litres_per_day"], 0)
        events = doses["irrigation"]["events_per_day"]
        sessions_en = "in one session" if events == 1 else f"in {events} sessions"
        sessions_ta = "ஒரே முறையில்" if events == 1 else f"{events} முறையாகப் பிரித்து"
        en.append(f"Water: {litres} litres today for {area} by {method}, {sessions_en}"
                  + (", before 07:00." if dawn else "."))
        ta.append(f"நீர்: இன்று {_fmt(area_acres)} ஏக்கருக்கு {litres} லிட்டர், {sessions_ta}"
                  + (", காலை 7 மணிக்கு முன் பாய்ச்சவும்." if dawn else " பாய்ச்சவும்."))
    if doses and doses.get("fertilizer") and decision in FERTILIZER_DECISIONS:
        kg = doses["fertilizer"]["kg_area"]
        # Leave out products with no dose (e.g. urea when DAP already supplies the nitrogen).
        products = [(en_name, ta_name, kg[key]) for key, en_name, ta_name in (
            ("urea_net", "Urea", "யூரியா"), ("dap", "DAP", "டிஏபி"), ("mop", "MOP", "பொட்டாஷ் (எம்ஓபி)"))
            if round(kg[key], 1) > 0]
        en.append(f"Fertilizer for {area}: " + ", ".join(f"{n} {_fmt(v)} kg" for n, _, v in products) + ".")
        ta.append(f"{_fmt(area_acres)} ஏக்கருக்கு உரம்: " + ", ".join(f"{t} {_fmt(v)} கிலோ" for _, t, v in products) + ".")

    pct = _fmt(confidence["score"] * 100, 0)
    en.append(f"Confidence: {confidence['level']} ({pct}%).")
    ta.append(f"நம்பகத்தன்மை: {confidence['level']} ({pct}%).")
    en.append(DISCLAIMER_EN)
    ta.append(DISCLAIMER_TA)
    return {"en": " ".join(en), "ta": " ".join(ta)}


def _contract_answer(urgency: str, advisory: dict) -> str:
    """The judges' answer format: URGENCY / ADVICE / Tamil advice / disclaimer."""
    en = advisory["en"].removesuffix(" " + DISCLAIMER_EN)
    ta = advisory["ta"].removesuffix(" " + DISCLAIMER_TA)
    return f"URGENCY: {urgency}\nADVICE: {en}\nஆலோசனை: {ta}\n{DISCLAIMER_EN}"


def _rounded(d: dict, digits: int = 2) -> dict:
    return {k: (_rounded(v, digits) if isinstance(v, dict)
                else round(v, digits) if isinstance(v, float) else v)
            for k, v in d.items()}


def run_advisory(
    df: pd.DataFrame,
    area_acres: float,
    irrigation: str,
    days_after_transplanting: int,
    lat: float,
    lon: float,
    crop: str | None = None,
    soil: str | None = None,
    stage: str | None = None,
    weather: WeatherRisk | None = None,
    cfg: dict | None = None,
) -> dict:
    """Run the full pipeline on a telemetry frame. `crop` defaults to the telemetry's crop column, then
    the configured default. `stage` overrides the stage derived from days_after_transplanting.
    Raises ValueError on unusable input."""
    cfg = cfg or load_agronomy()
    if area_acres <= 0:
        raise ValueError("area_acres must be greater than 0")
    if days_after_transplanting < 0:
        raise ValueError("days_after_transplanting cannot be negative")
    moisture = _latest(df, "moisture")
    if moisture is None:
        raise ValueError("telemetry needs a numeric 'moisture' column")

    crop = resolve_crop(crop or _csv_crop(df), cfg)
    crop_cfg = cfg["crops"][crop]
    flooded = bool(crop_cfg.get("flooded"))
    method = "flood" if flooded else irrigation
    thresholds = moisture_thresholds(soil, cfg, crop)
    trigger, fc, pwp = thresholds["trigger"], thresholds["fc"], thresholds["pwp"]
    trace: list[dict] = []

    quality = check_quality(df)
    trace.append({"step": "quality", "tool": "check_quality", "observation": asdict(quality)})
    # A ponded paddy reads a constant, saturated moisture: that flatline is expected, not a fault.
    ponded = flooded and moisture >= fc
    sensor_fault = any(i.column == "moisture" and i.severity == "CRITICAL"
                       and (i.code == "OUT_OF_RANGE" or (i.code == "FLATLINE" and not ponded))
                       for i in quality.issues)

    trends = analyze_trends(df, {"trigger_moisture": trigger, "heat_threshold_c": cfg["heat_threshold_c"]})
    trends_out = {k: asdict(v) for k, v in trends.items()}
    trace.append({"step": "trends", "tool": "analyze_trends", "observation": trends_out})

    weather = weather or get_weather_risk(lat, lon)
    trace.append({"step": "weather", "tool": "get_weather_risk", "observation": asdict(weather)})

    stage, requirement = stage_requirement(crop, stage, days_after_transplanting, cfg)
    measured = {n: _latest(df, n) for n in ("N", "P", "K")}
    missing_npk = any(v is None for v in measured.values())
    fertilizer = None if missing_npk else nutrient_dose(measured, requirement, area_acres, cfg)
    fertilizer_due = bool(fertilizer) and any(v > 0 for v in fertilizer["deficit_kg_ha"].values())
    trace.append({"step": "fertilizer", "tool": "nutrient_dose",
                  "observation": {"stage": stage, "requirement_kg_ha": requirement, "measured": measured,
                                  "plan": fertilizer and _rounded(fertilizer)}})

    eff_rain = effective_rain_mm(weather.rain_mm_48h, weather.rain_prob_48h, cfg)
    if irrigation not in ("drip", "flood"):
        irrigation_litres(moisture, area_acres, irrigation, thresholds, cfg)  # raises the method error
    water = (flood_litres(moisture, area_acres, thresholds, crop_cfg["flood_depth_mm"], cfg, eff_rain_mm=eff_rain)
             if flooded else
             irrigation_litres(moisture, area_acres, method, thresholds, cfg, eff_rain_mm=eff_rain))
    trace.append({"step": "irrigation", "tool": "flood_litres" if flooded else "irrigation_litres",
                  "observation": _rounded({**water, "effective_rain_mm": eff_rain})})

    rules = fire_rules(
        irrigation_needed=moisture < trigger,
        rain_mm_48h=weather.rain_mm_48h,
        rain_prob_48h=weather.rain_prob_48h,
        fertilizer_due=fertilizer_due,
        moisture=moisture,
        fc=fc,
        trigger=trigger,
        tmax_next3=weather.tmax_next3,
        cfg=cfg,
        has_sensor_fault=sensor_fault,
        flooded=flooded,
    )
    trace.append({"step": "rules", "tool": "fire_rules", "observation": rules})

    codes = {(i.code, i.severity) for i in quality.issues}
    score, reasons, level = compute_score(
        cfg,
        has_flatline=("FLATLINE", "CRITICAL") in codes and not ponded,
        has_gap=("GAP", "WARN") in codes,
        has_spike=("SPIKE", "WARN") in codes,
        weather_fallback=weather.source == "fallback",
        missing_npk=missing_npk,
        less_than_5_days=_days_of_data(df) < 5,
        dataset_targets=targets_from_dataset(crop, cfg) and not missing_npk,
        sensor_fault=sensor_fault,
    )
    confidence = {"score": score, "level": level, "reasons": reasons}
    trace.append({"step": "confidence", "tool": "compute_score", "observation": confidence})

    fit = crop_fit({**measured, "temperature": _latest(df, "temperature"), "humidity": _latest(df, "humidity"),
                    "ph": _latest(df, "pH")}, crop=crop)
    trace.append({"step": "crop_fit", "tool": "crop_fit", "observation": fit})

    decision = rules["decision"]
    urgency = URGENCY[decision]
    doses = None if sensor_fault else {
        "fertilizer": fertilizer and _rounded(fertilizer),
        "irrigation": _rounded(water),
        "method": method,
    }
    advisory = _advisory(decision, crop, stage, flooded, moisture, trigger, area_acres, method, doses,
                         "R4_HEAT_DAWN" in rules["fired_rules"], confidence)
    if flooded:
        water_rule = (f"rice is kept ponded: re-flood to {crop_cfg['flood_depth_mm']} mm (TNAU) once moisture "
                      f"drops below field capacity ({trigger}%), flood efficiency")
    else:
        water_rule = (f"irrigation trigger={trigger}% = FC - {crop_cfg['p']} x (FC - PWP) (FAO-56 p for {crop}); "
                      "refill to field capacity, capped per day")
    return {
        "decision": decision,
        "urgency": urgency,
        "crop": crop,
        "stage": stage,
        "confidence": confidence,
        "rules_fired": rules["fired_rules"],
        "reasons": rules["reasons"],
        "advisory": advisory,
        "answer": _contract_answer(urgency, advisory),
        "readings": {"moisture": moisture, **measured},
        "moisture_thresholds": thresholds,
        "doses": doses,
        "weather": asdict(weather),
        "quality": asdict(quality),
        "trends": trends_out,
        "crop_fit": fit,
        "assumptions": [
            f"crop={crop}, stage={stage}" + (" (no stage-specific targets for this crop)"
                                             if stage == WHOLE_SEASON else ""),
            f"soil={thresholds['soil']}: field capacity {fc}%, wilting point {pwp}% (volumetric)",
            water_rule,
            f"N/P/K readings treated as {cfg['npk_unit']} against crop requirements",
            *([f"no TNAU recommendation for {crop} here: N/P/K target {requirement} is the median of its rows in "
               "the Kaggle Crop Recommendation dataset"] if targets_from_dataset(crop, cfg) else []),
            "urea shown is net of the nitrogen already supplied by DAP",
        ],
        "trace": trace,
    }
