"""Shared dataclasses for the Sensor-to-Dose Advisor core pipeline.

All types are plain dataclasses with no dependencies on LLM, network, or web
frameworks.  Kept dependency-free so each core module can be unit-tested in
isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Issue:
    """A single data-quality problem detected in the telemetry."""

    code: str
    severity: str  # "INFO" | "WARN" | "CRITICAL"
    detail: str
    column: str | None = None  # standard column name, None for frame-level issues (GAP)


@dataclass
class QualityReport:
    """Result of telemetry quality checks."""

    score: float  # 0..1 data-quality score (before confidence deductions)
    issues: list[Issue] = field(default_factory=list)


@dataclass
class TrendReport:
    """Trend analysis over the last 7 days (or fewer if data is short)."""

    column: str
    readings: int
    latest: float
    slope_per_day: float
    status: str  # "falling" | "rising" | "stable"
    days_to_trigger: float | None = None
    min_24h: float | None = None
    max_24h: float | None = None
    heat_stress_hours: int = 0
    wetting_events: int = 0


@dataclass
class WeatherRisk:
    """Weather-derived risk for the upcoming days."""

    rain_mm_48h: float
    rain_prob_48h: float
    tmax_next3: float
    source: str  # "live" | "cache" | "fallback"


@dataclass
class NutrientDose:
    """Computed dose for a single nutrient (N / P / K)."""

    nutrient: str
    measured: float
    target: float
    deficit: float  # kg/ha (when npk_unit == kg_ha)
    product_kg_ha: float
    product_kg_total: float  # for the given area
    product_name: str
    product_pct: float
    splits: list[dict] = field(default_factory=list)


@dataclass
class IrrigationDose:
    """Computed irrigation dose."""

    trigger: float
    vwc_now: float
    deficit_mm: float
    net_mm: float
    litres: float
    area_m2: float
    efficiency: float
    eff_rain_mm: float


@dataclass
class DosageResult:
    """Full dosage computation result."""

    crop: str
    stage: str
    area_acres: float
    area_m2: float
    npk_unit: str
    assumptions: list[str] = field(default_factory=list)
    nutrients: list[NutrientDose] = field(default_factory=list)
    irrigation: IrrigationDose | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class RuleResult:
    """A single fired rule from the cross-signal engine."""

    id: str
    reason: str
    decision: str


@dataclass
class ConfidenceResult:
    """Confidence score and reasoning."""

    score: float  # 0..1
    level: str  # "HIGH" | "MEDIUM" | "LOW"
    reasons: list[str] = field(default_factory=list)


@dataclass
class CalendarEntry:
    """A single dated action in the 7-day plan."""

    date: str
    action: str
    quantity: str
    why: str


@dataclass
class ImpactResult:
    """Water / money savings estimate vs the baseline fixed schedule."""

    litres_saved: float
    rupees_saved: float
    baseline_text: str


@dataclass
class WhatIfResult:
    """Projection when skipping irrigation for N days."""

    skip_days: int
    projected_moisture: list[float]  # one value per skipped day
    cross_trigger_day: int | None
    verdict: str


@dataclass
class CropFitResult:
    """Kaggle crop-recommendation fit check (tomato not in labels)."""

    tomato_in_labels: bool
    message: str
    better_crops: list[str] = field(default_factory=list)


@dataclass
class AdvisoryResult:
    """Final structured advisory output."""

    decision: str
    confidence: ConfidenceResult
    advisory_en: str
    advisory_ta: str
    dosage: DosageResult
    calendar: list[CalendarEntry]
    impact: ImpactResult
    rules_fired: list[RuleResult]
    assumptions: list[str]
    trace: list[dict] = field(default_factory=list)
    as_of: str | None = None
    demo_mode: bool = False
