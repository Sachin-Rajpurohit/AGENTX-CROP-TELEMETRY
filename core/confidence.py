"""Confidence scoring module.

Score = 1.0 minus weighted deductions from config/agronomy.yaml
(flatline, gap, spike, weather fallback, missing NPK, <5 days of data).
A sensor fault caps the score (rule R5).
Mapped to HIGH/MEDIUM/LOW with the reasons shown to the farmer.
"""
from __future__ import annotations


def confidence_level(score: float, cfg: dict) -> str:
    if score >= cfg["confidence_high"]:
        return "HIGH"
    if score >= cfg["confidence_medium"]:
        return "MEDIUM"
    return "LOW"


def compute_score(
    cfg: dict,
    has_flatline: bool = False,
    has_gap: bool = False,
    has_spike: bool = False,
    weather_fallback: bool = False,
    missing_npk: bool = False,
    less_than_5_days: bool = False,
    dataset_targets: bool = False,
    sensor_fault: bool = False,
) -> tuple[float, list[str], str]:
    """Return (score in [0, 1], reasons, level)."""
    deductions = [
        (has_flatline, "deduct_flatline", "flatline sensor reading"),
        (has_gap, "deduct_gap", "data gap > 2x median interval"),
        (has_spike, "deduct_spike", "sensor spike detected"),
        (weather_fallback, "deduct_weather_fallback", "live weather unavailable, used fallback forecast"),
        (missing_npk, "deduct_missing_npk", "missing NPK readings"),
        (less_than_5_days, "deduct_lt5_days", "< 5 days of data"),
        (dataset_targets, "deduct_dataset_targets", "fertilizer target from crop dataset, not a TNAU recommendation"),
    ]
    score = 1.0
    reasons: list[str] = []
    for applies, key, reason in deductions:
        if applies:
            score -= cfg[key]
            reasons.append(reason)

    if sensor_fault and score > cfg["sensor_fault_confidence_cap"]:
        score = cfg["sensor_fault_confidence_cap"]
        reasons.append("sensor fault: confidence capped")

    score = round(max(0.0, min(1.0, score)), 2)
    return score, reasons, confidence_level(score, cfg)
