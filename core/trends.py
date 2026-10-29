"""Trend analysis over the last 7 days of telemetry.

Resamples to daily means, detects wetting events, fits the drying slope on the
latest segment after the last wetting event, and projects days to the
irrigation trigger.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import schema
from core.quality import SYNONYMS


def _resolve_column(df: pd.DataFrame, standard: str) -> str | None:
    """Return the actual dataframe column name for a standard key, or None."""
    for actual in df.columns:
        if actual.lower() in SYNONYMS.get(standard, []):
            return actual
    return None


def analyze_trends(df: pd.DataFrame, cfg: dict) -> dict[str, schema.TrendReport]:
    """Analyze trends for moisture, N, P, K, temperature over the last 7 days.

    Parameters
    ----------
    df : pd.DataFrame
        Raw telemetry with a timestamp column.
    cfg : dict
        Configuration with keys ``trigger_moisture`` and ``heat_threshold_c``.

    Returns
    -------
    dict[str, schema.TrendReport]
        One report per available standard column, keyed by standard name.
    """
    reports: dict[str, schema.TrendReport] = {}
    trigger = float(cfg.get("trigger_moisture", 65))
    heat_threshold = float(cfg.get("heat_threshold_c", 35))

    ts_col = _resolve_column(df, "timestamp")
    if ts_col is None:
        return reports

    df2 = df.copy()
    df2["_ts"] = pd.to_datetime(df2[ts_col], errors="coerce")
    df2 = df2.dropna(subset=["_ts"]).sort_values("_ts")
    if df2.empty:
        return reports
    df2 = df2.set_index("_ts")

    # Resample to daily means, then take the last 7 days.
    daily = df2.resample("D").mean(numeric_only=True).tail(7)

    for standard in ["moisture", "N", "P", "K", "temperature"]:
        col = _resolve_column(df, standard)
        if col is None or col not in daily.columns:
            continue
        series = daily[col].dropna()
        if len(series) < 2:
            continue

        latest = float(series.iloc[-1])
        x = np.arange(len(series), dtype=float)
        y = series.values.astype(float)
        slope = float(np.polyfit(x, y, 1)[0])
        status = (
            "falling"
            if slope < -0.05
            else ("rising" if slope > 0.05 else "stable")
        )

        days_to_trigger: float | None = None
        min_24h: float | None = None
        max_24h: float | None = None
        heat_stress_hours = 0
        wetting_events = 0

        if standard == "moisture":
            # Wetting events: day-over-day moisture jump > 3 points.
            diffs = series.diff().dropna()
            wetting_events = int((diffs > 3.0).sum())

            # Latest segment starts after the last wetting event.
            last_wet_idx: int | None = None
            for i in range(1, len(series)):
                if float(series.iloc[i] - series.iloc[i - 1]) > 3.0:
                    last_wet_idx = i
            seg = series
            if last_wet_idx is not None and last_wet_idx < len(series) - 1:
                seg = series.iloc[last_wet_idx:]

            if len(seg) >= 2:
                sx = np.arange(len(seg), dtype=float)
                sy = seg.values.astype(float)
                seg_slope = float(np.polyfit(sx, sy, 1)[0])
            else:
                seg_slope = slope

            if seg_slope < 0 and latest > trigger:
                days_to_trigger = (latest - trigger) / abs(seg_slope)

        if standard == "temperature":
            raw = pd.to_numeric(df2[col], errors="coerce").dropna()
            heat_stress_hours = int((raw >= heat_threshold).sum())

        min_24h = float(series.min())
        max_24h = float(series.max())

        reports[standard] = schema.TrendReport(
            column=standard,
            readings=len(series),
            latest=latest,
            slope_per_day=slope,
            status=status,
            days_to_trigger=days_to_trigger,
            min_24h=min_24h,
            max_24h=max_24h,
            heat_stress_hours=heat_stress_hours,
            wetting_events=wetting_events,
        )

    return reports
