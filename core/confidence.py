"""Confidence scoring module.

Score = 1.0 minus weighted deductions from config:
  flatline 0.35, gap 0.10, spike 0.05, weather fallback 0.15,
  missing NPK 0.20, <5 days of data 0.15.

Return (score, reasons[]). Map to HIGH/MEDIUM/LOW with the reasons
shown to the farmer.
"""
from __future__ import annotations

from typing import List, Tuple


# Thresholds for confidence levels
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.5


def compute_score(
    has_flatline: bool = False,
    has_gap: bool = False,
    has_spike: bool = False,
    weather_fallback: bool = False,
    missing_npk: bool = False,
    less_than_5_days: bool = False,
) -> Tuple[float, List[str]]:
    """Compute confidence score and deduction reasons.

    Returns (score, reasons) where score is in [0, 1].
    """
    score = 1.0
    reasons: List[str] = []

    # FLATLINE deduction
    if has_flatline:
        score -= 0.35
        reasons.append("flatline sensor reading")

    # GAP deduction
    if has_gap:
        score -= 0.10
        reasons.append("data gap > 2x median interval")

    # SPIKE deduction
    if has_spike:
        score -= 0.05
        reasons.append("sensor spike detected")

    # Weather fallback deduction
    if weather_fallback:
        score -= 0.15
        reasons.append("weather API fallback used")

    # Missing NPK deduction
    if missing_npk:
        score -= 0.20
        reasons.append("missing NPK columns in input")

    # <5 days of data deduction
    if less_than_5_days:
        score -= 0.15
        reasons.append("< 5 days of data")

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    # Map to level
    if score >= CONFIDENCE_HIGH:
        level = "HIGH"
    elif score >= CONFIDENCE_MEDIUM:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, reasons, level


def confidence_level(score: float) -> str:
    """Return confidence level string for a given score."""
    if score >= CONFIDENCE_HIGH:
        return "HIGH"
    elif score >= CONFIDENCE_MEDIUM:
        return "MEDIUM"
    return "LOW"