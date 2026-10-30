"""Cross-signal engine returning fired rules with id + plain reason.

Every rule whose condition holds fires; the decision is the highest-priority
fired rule. Thresholds come from config/agronomy.yaml.

R5 FLATLINE_HOLD: sensor fault (critical FLATLINE / OUT_OF_RANGE on moisture) -> INSPECT_SENSOR, no dose numbers
R6 SATURATED: moisture >= fc (not for flooded rice) -> DRAINAGE_WARNING, no irrigation
R1 RAIN_SKIP_IRRIGATION: irrigation needed AND rain_mm_48h >= 8 AND prob >= 60 -> WAIT_FOR_RAIN
R2 RAIN_DELAY_FERT: fertilizer due AND rain_mm_48h >= 25 -> DELAY_FERTILIZER (leaching and runoff)
R3 DRY_NO_FERT: fertilizer due AND moisture below trigger -> IRRIGATE_THEN_FERTILIZE (root burn)
R9 IRRIGATE: moisture below trigger -> IRRIGATE
R10 FERTILIZE: N/P/K below stage requirement -> FERTILIZE
R4 HEAT_DAWN: tmax_next3 >= 35 while irrigating -> irrigate before 07:00 (timing modifier)
R7 DOSE_CAP: a computed dose was clipped to its cap (flag only)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    decision: str
    reason: str


R5 = Rule("R5_FLATLINE_HOLD", "INSPECT_SENSOR",
          "Sensor fault detected: no dose numbers given, confidence capped")
R6 = Rule("R6_SATURATED", "DRAINAGE_WARNING",
          "Soil at or above field capacity: no irrigation needed, check drainage")
R1 = Rule("R1_RAIN_SKIP_IRRIGATION", "WAIT_FOR_RAIN",
          "Rain likely within 48h: skip irrigation to avoid runoff and save water")
R2 = Rule("R2_RAIN_DELAY_FERT", "DELAY_FERTILIZER",
          "Heavy rain expected: delay fertilizer to avoid leaching and runoff")
R3 = Rule("R3_DRY_NO_FERT", "IRRIGATE_THEN_FERTILIZE",
          "Never apply fertilizer into dry soil (root burn risk): irrigate first")
R9 = Rule("R9_IRRIGATE", "IRRIGATE",
          "Soil moisture is below the irrigation trigger")
R10 = Rule("R10_FERTILIZE", "FERTILIZE",
           "Nutrient levels are below the growth-stage requirement")
R4 = Rule("R4_HEAT_DAWN", "IRRIGATE_AT_DAWN",
          "Heat expected: irrigate before 07:00 to cut evaporative loss")
R7 = Rule("R7_DOSE_CAP", "NO_ACTION",
          "A computed dose was clipped to its configured maximum")
NO_ACTION = Rule("R8_NO_ACTION", "NO_ACTION",
                 "Conditions do not trigger any advisory action")

# Highest priority first. R4 and R7 are modifiers and never set the decision.
DECISION_PRIORITY = [R5, R6, R1, R2, R3, R9, R10]


def fire_rules(
    irrigation_needed: bool,
    rain_mm_48h: float,
    rain_prob_48h: float,
    fertilizer_due: bool,
    moisture: float,
    fc: float,
    trigger: float,
    tmax_next3: float,
    cfg: dict,
    has_sensor_fault: bool = False,
    computed_doses_exceed_cap: bool = False,
    flooded: bool = False,
) -> dict:
    """Return {"decision", "fired_rules": [ids], "reasons": [str]}. `flooded` crops (ponded rice)
    are meant to be saturated, so R6 never fires for them."""
    rain_likely = (rain_mm_48h >= cfg["rain_skip_threshold_mm"]
                   and rain_prob_48h >= cfg["rain_skip_prob_pct"])
    conditions = {
        R5: has_sensor_fault,
        R6: moisture >= fc and not flooded,
        R1: irrigation_needed and rain_likely,
        R2: fertilizer_due and rain_mm_48h >= cfg["rain_delay_threshold_mm"],
        R3: fertilizer_due and moisture < trigger,
        R9: irrigation_needed,
        R10: fertilizer_due,
    }
    if has_sensor_fault:
        # Readings can't be trusted, so no other rule is meaningful.
        conditions = {R5: True}

    fired = [r for r in DECISION_PRIORITY if conditions.get(r)]
    decision = fired[0].decision if fired else NO_ACTION.decision

    if decision in ("IRRIGATE", "IRRIGATE_THEN_FERTILIZE") and tmax_next3 >= cfg["heat_threshold_c"]:
        fired.append(R4)
    if computed_doses_exceed_cap and not has_sensor_fault:
        fired.append(R7)
    if not fired:
        fired.append(NO_ACTION)

    return {
        "decision": decision,
        "fired_rules": [r.id for r in fired],
        "reasons": [r.reason for r in fired],
    }
