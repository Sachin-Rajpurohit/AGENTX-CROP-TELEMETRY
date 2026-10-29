"""Telemetry quality checks.

Interval-aware: the median sampling interval is derived from the timestamps at
runtime, so FLATLINE / GAP thresholds scale with the actual cadence rather than
being hard-coded to daily.
"""

from __future__ import annotations

import pandas as pd

from core import schema

SYNONYMS = {
    "moisture": ["moisture", "soil_moisture", "soilmoisture", "vwc"],
    "N": ["n", "nitrogen"],
    "P": ["p", "phosphorus", "phosphorous"],
    "K": ["k", "potassium"],
    "pH": ["ph"],
    "temperature": ["temperature", "temp"],
    "humidity": ["humidity"],
    "rainfall": ["rainfall", "rain"],
    "timestamp": ["timestamp", "time", "date", "datetime"],
}

FLATLINE_INFO_ONLY = {"N", "P", "K"}
FLATLINE_COLUMNS = ["moisture", "temperature", "humidity"]

RANGE_BOUNDS = {
    "moisture": (0.0, 100.0),
    "pH": (3.0, 10.0),
    "temperature": (-5.0, 60.0),
}


def _resolve_column(df: pd.DataFrame, standard: str) -> str | None:
    """Return the actual dataframe column name for a standard key, or None."""
    for actual in df.columns:
        if actual.lower() in SYNONYMS.get(standard, []):
            return actual
    return None


def _median_interval_hours(df: pd.DataFrame) -> float | None:
    """Derive the median sampling interval in hours from the timestamp column."""
    ts_col = _resolve_column(df, "timestamp")
    if ts_col is None:
        return None
    times = pd.to_datetime(df[ts_col], errors="coerce").dropna().sort_values()
    if len(times) < 2:
        return None
    diffs = times.diff().dropna()
    if diffs.empty:
        return None
    return float(diffs.median().total_seconds() / 3600.0)

def check_quality(df: pd.DataFrame) -> schema.QualityReport:
    """Run quality checks on the telemetry frame.

    Detects FLATLINE, OUT_OF_RANGE, SPIKE, GAP and MISSING_COLUMN.  Constant
    N/P/K is reported as an INFO note only — it is not a sensor fault.
    """
    issues: list[schema.Issue] = []
    interval_h = _median_interval_hours(df)

    # --- MISSING_COLUMN ----------------------------------------------------
    for standard in ["moisture", "N", "P", "K", "pH", "temperature"]:
        if _resolve_column(df, standard) is None:
            issues.append(
                schema.Issue(
                    code="MISSING_COLUMN",
                    severity="WARN",
                    detail=f"required column '{standard}' not found in CSV",
                )
            )

    # --- Per-column checks -------------------------------------------------
    for standard in [
        "moisture",
        "temperature",
        "humidity",
        "N",
        "P",
        "K",
        "pH",
    ]:
        col = _resolve_column(df, standard)
        if col is None:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        vals = series.dropna().tolist()

        # OUT_OF_RANGE.
        lo, hi = RANGE_BOUNDS.get(standard, (None, None))
        if lo is not None and hi is not None:
            for v in vals:
                if v < lo or v > hi:
                    issues.append(
                        schema.Issue(
                            code="OUT_OF_RANGE",
                            severity="CRITICAL",
                            detail=f"{standard}={v} outside [{lo}, {hi}]",
                        )
                    )
                    break

        # FLATLINE (only on FLATLINE_COLUMNS; constant N/P/K -> INFO note).
        if standard in FLATLINE_COLUMNS and len(vals) >= 3:
            run = _consecutive_identical_run(vals)
            if run >= 3:
                issues.append(
                    schema.Issue(
                        code="FLATLINE",
                        severity="CRITICAL",
                        detail=f"{standard} flatlined for {run} consecutive readings (last value {vals[-1]})",
                    )
                )
        elif standard in FLATLINE_INFO_ONLY and len(vals) >= 2:
            if all(v == vals[0] for v in vals):
                issues.append(
                    schema.Issue(
                        code="FLATLINE",
                        severity="INFO",
                        detail=f"{standard} constant at {vals[0]} across {len(vals)} readings (expected; no dose impact)",
                    )
                )

        # SPIKE (only when 6+ points).
        if len(vals) >= 6:
            svals = pd.Series(vals)
            median = float(svals.median())
            mad = float((svals - median).abs().median())
            if mad > 0:
                for i, v in enumerate(vals):
                    if abs(v - median) > 4 * mad:
                        issues.append(
                            schema.Issue(
                                code="SPIKE",
                                severity="WARN",
                                detail=(
                                    f"{standard} spike at index {i}: {v} "
                                    f"(median {median:.2f}, MAD {mad:.2f})"
                                ),
                            )
                        )
                        break

    # --- GAP ---------------------------------------------------------------
    if interval_h is not None:
        ts_col = _resolve_column(df, "timestamp")
        if ts_col is not None:
            times = pd.to_datetime(df[ts_col], errors="coerce").dropna().sort_values()
            diffs = times.diff().dropna()
            gap_threshold_h = interval_h * 2.0
            for d in diffs:
                if d.total_seconds() / 3600.0 > gap_threshold_h:
                    issues.append(
                        schema.Issue(
                            code="GAP",
                            severity="WARN",
                            detail=(
                                f"gap of {d.total_seconds()/3600.0:.1f}h > "
                                f"{gap_threshold_h:.1f}h (2x median interval)"
                            ),
                        )
                    )
                    break

    # Quality score: 1.0 minus small per-issue deductions.
    deduct = 0.0
    for iss in issues:
        if iss.severity == "CRITICAL":
            deduct += 0.25
        elif iss.severity == "WARN":
            deduct += 0.10
        else:
            deduct += 0.02
    score = max(0.0, min(1.0, 1.0 - deduct))

    return schema.QualityReport(score=score, issues=issues)


def _consecutive_identical_run(values: list[float]) -> int:
    """Length of the run of consecutive identical values at the end of the list."""
    if not values:
        return 0
    run = 1
    for i in range(len(values) - 2, -1, -1):
        if values[i] == values[i + 1]:
            run += 1
        else:
            break
    return run
