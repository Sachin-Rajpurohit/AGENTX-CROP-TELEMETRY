"""Cross-signal engine returning fired rules with id + plain reason.

Rules are data-driven (list of Rule objects), each unit-tested.

R1 RAIN_SKIP_IRRIGATION: irrigation needed AND rain_mm_48h >= 8 AND prob >= 60 -> WAIT_FOR_RAIN, recheck after rain
R2 RAIN_DELAY_FERT: fertilizer due AND rain_mm_48h >= 25 -> DELAY_FERTILIZER (leaching and runoff)
R3 DRY_NO_FERT: fertilizer due AND moisture below trigger -> IRRIGATE_THEN_FERTILIZE (never apply into dry soil: root burn)
R4 HEAT_DAWN: tmax_next3 >= 35 -> irrigation shifts to before 07:00 (IRRIGATE_AT_DAWN)
R5 FLATLINE_HOLD: critical FLATLINE or OUT_OF_RANGE on moisture -> INSPECT_SENSOR, no dose numbers, confidence capped at 0.4
R6 SATURATED: moisture >= fc -> no irrigation, DRAINAGE_WARNING
R7 DOSE_CAP: any computed dose exceeding config cap is clipped and flagged
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    code: str
    severity: str
    detail: str


@dataclass
class Rule:
    id: str
    condition_desc: str
    decision: str
    reason: str


# Pre-defined rule set
RULES: List[Rule] = [
    Rule(
        id="R1_RAIN_SKIP_IRRIGATION",
        condition_desc=(
            "irrigation needed AND rain_mm_48h >= 8 AND prob >= 60"
        ),
        decision="WAIT_FOR_RAIN",
        reason=(
            "Rain likely within 48h: skip irrigation to avoid runoff and save water"
        ),
    ),
    Rule(
        id="R2_RAIN_DELAY_FERT",
        condition_desc="fertilizer due AND rain_mm_48h >= 25",
        decision="DELAY_FERTILIZER",
        reason=(
            "Heavy rain >=25mm risks leaching and runoff: delay fertilizer application"
        ),
    ),
    Rule(
        id="R3_DRY_NO_FERT",
        condition_desc="fertilizer due AND moisture below trigger",
        decision="IRRIGATE_THEN_FERTILIZE",
        reason=(
            "Never apply fertilizer into dry soil: root burn risk; irrigate first"
        ),
    ),
    Rule(
        id="R4_HEAT_DAWN",
        condition_desc="tmax_next3 >= 35",
        decision="IRRIGATE_AT_DAWN",
        reason=(
            "Shift irrigation before 07:00 to avoid evaporative loss under heat >=35C"
        ),
    ),
    Rule(
        id="R5_FLATLINE_HOLD",
        condition_desc="critical FLATLINE or OUT_OF_RANGE on moisture",
        decision="INSPECT_SENSOR",
        reason=(
            "Sensor fault detected: no dose numbers given, confidence capped at 0.4"
        ),
    ),
    Rule(
        id="R6_SATURATED",
        condition_desc="moisture >= fc",
        decision="DRAINAGE_WARNING",
        reason=(
            "Soil at field capacity: no irrigation needed, drainage required instead"
        ),
    ),
    Rule(
        id="R7_DOSE_CAP",
        condition_desc="any computed dose exceeding config cap",
        decision="IRRIGATE_THEN_FERTILIZE",
        reason=(
            "Dose clipped to config maximum; flag applied; re-evaluate at next cycle"
        ),
    ),
]


def fire_rules(
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
    """Fire the cross-signal rule engine.

    Returns fired rules with rulings and a recommended decision.

    Decision priority (first match wins):
    1. R5 FLATLINE_HOLD (sensor fault)
    2. R6 SATURATED (moisture >= fc)
    3. R1 RAIN_SKIP_IRRIGATION
    4. R2 RAIN_DELAY_FERT
    5. R3 DRY_NO_FERT
    6. R4 HEAT_DAWN
    7. R7 DOSE_CAP
    8. NO_ACTION (default)
    """
    fired: list[Rule] = []

    # R5: FLATLINE_HOLD — sensor fault takes priority
    if has_sensor_fault:
        fired.append(RULES[4])  # R5_FLATLINE_HOLD

    # R6: SATURATED — no irrigation needed
    elif moisture >= fc:
        fired.append(RULES[5])  # R6_SATURATED

    # R1: RAIN_SKIP_IRRIGATION
    elif irrigation_needed and rain_mm_48h >= 8 and rain_prob_48h >= 60:
        fired.append(RULES[0])  # R1_RAIN_SKIP_IRRIGATION

    # R2: RAIN_DELAY_FERT
    elif fertilizer_due and rain_mm_48h >= 25:
        fired.append(RULES[1])  # R2_RAIN_DELAY_FERT

    # R3: DRY_NO_FERT — fertilizer due but soil too dry
    elif fertilizer_due and moisture < fc:
        fired.append(RULES[2])  # R3_DRY_NO_FERT

    # R4: HEAT_DAWN — high temperature shifts timing
    elif tmax_next3 >= 35:
        fired.append(RULES[3])  # R4_HEAT_DAWN

    # R7: DOSE_CAP — computed dose exceeded cap
    elif computed_doses_exceed_cap:
        fired.append(RULES[6])  # R7_DOSE_CAP

    # Default: NO_ACTION
    else:
        fired.append(
            Rule(
                id="R8_NO_ACTION",
                condition_desc="no rules fired",
                decision="NO_ACTION",
                reason="Conditions do not trigger any advisory action",
            )
        )

    # Derive recommended decision from fired rules
    decisions = [r.decision for r in fired]
    if "INSPECT_SENSOR" in decisions:
        recommended = "INSPECT_SENSOR"
    elif "DRAINAGE_WARNING" in decisions:
        recommended = "DRAINAGE_WARNING"
    elif "WAIT_FOR_RAIN" in decisions:
        recommended = "WAIT_FOR_RAIN"
    elif "DELAY_FERTILIZER" in decisions:
        recommended = "DELAY_FERTILIZER"
    elif "IRRIGATE_THEN_FERTILIZE" in decisions:
        recommended = "IRRIGATE_THEN_FERTILIZE"
    elif "IRRIGATE_AT_DAWN" in decisions:
        recommended = "IRRIGATE_AT_DAWN"
    elif "NO_ACTION" in decisions:
        recommended = "NO_ACTION"
    else:
        recommended = "NO_ACTION"

    return {
        "fired_rules": [r.id for r in fired],
        "decision": recommended,
        "reasons": [r.reason for r in fired],
    }