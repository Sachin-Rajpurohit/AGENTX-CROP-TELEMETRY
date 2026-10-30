"""Crop suitability from the Kaggle Crop Recommendation dataset (22 crops x 100 rows).

For each crop the dataset gives N, P, K, temperature, humidity, pH and rainfall where it grows well.
A field fits a crop when its readings fall inside that crop's typical (10th-90th percentile) range.
Rainfall is excluded: the dataset's rainfall is seasonal mm, telemetry rainfall is per reading.
The dataset has no tomato, so tomato fields are compared against the 22 crops it does cover.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATASET = Path(__file__).resolve().parents[1] / "data" / "Crop_recommendation.csv"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph"]
MIN_FEATURES = 3


@lru_cache(maxsize=1)
def _profiles() -> dict[str, pd.DataFrame]:
    """Per-crop p10 / p90 / mean / std for each feature."""
    df = pd.read_csv(DATASET)
    g = df.groupby("label")[FEATURES]
    stats = {"p10": g.quantile(0.10), "p90": g.quantile(0.90), "mean": g.mean(), "std": g.std()}
    return {crop: pd.DataFrame({k: v.loc[crop] for k, v in stats.items()}) for crop in g.groups}


def dataset_targets(crop: str) -> dict[str, float]:
    """Median N, P, K of a crop's rows in the dataset: the typical level where it grows well."""
    profile = _profiles().get(crop)
    if profile is None:
        raise ValueError(f"{crop!r} is not in {DATASET.name}")
    df = pd.read_csv(DATASET)
    rows = df[df["label"] == crop]
    return {n: round(float(rows[n].median()), 1) for n in ("N", "P", "K")}


def crop_fit(readings: dict, crop: str | None = None, top_n: int = 3) -> dict:
    """Rank the dataset's crops by how many readings fall in their typical range (ties: closest
    to the crop's mean, in standard deviations). `readings` keys: N, P, K, temperature, humidity, ph."""
    used = {f: float(readings[f]) for f in FEATURES if readings.get(f) is not None}
    if len(used) < MIN_FEATURES:
        return {"available": False, "reason": f"need at least {MIN_FEATURES} of {FEATURES}, got {list(used)}"}
    try:
        profiles = _profiles()
    except FileNotFoundError:
        return {"available": False, "reason": f"{DATASET.name} not found"}

    ranked = []
    for name, prof in profiles.items():
        lo, hi = prof["p10"], prof["p90"]
        out = [f for f, v in used.items() if not lo[f] <= v <= hi[f]]
        dist = sum(abs(v - prof["mean"][f]) / prof["std"][f] for f, v in used.items()) / len(used)
        ranked.append({
            "crop": name,
            "in_range": len(used) - len(out),
            "of": len(used),
            "outside_typical_range": {f: {"value": used[f], "typical": [round(float(lo[f]), 1), round(float(hi[f]), 1)]}
                                      for f in out},
            "distance_sd": round(float(dist), 2),
        })
    ranked.sort(key=lambda r: (-r["in_range"], r["distance_sd"]))
    selected = next((r for r in ranked if crop and r["crop"] == crop.lower()), None)
    return {
        "available": True,
        "features_used": list(used),
        "best_matches": ranked[:top_n],
        "selected_crop": selected,
        "selected_crop_in_dataset": selected is not None,
        "source": "Kaggle Crop Recommendation dataset (atharvaingle), 22 crops",
    }
