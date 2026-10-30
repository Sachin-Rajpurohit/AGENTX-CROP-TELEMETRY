"""Loader for config/agronomy.yaml. Every agronomy constant lives in the YAML, not in code."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

AGRONOMY_YAML = Path(__file__).with_name("agronomy.yaml")


@lru_cache(maxsize=1)
def load_agronomy() -> dict:
    with open(AGRONOMY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def moisture_thresholds(soil: str | None = None, cfg: dict | None = None) -> dict:
    """FC, PWP and FAO-56 irrigation trigger (volumetric %) for a soil type."""
    cfg = cfg or load_agronomy()
    soil = soil or cfg["default_soil"]
    if soil not in cfg["soil_types"]:
        raise ValueError(f"soil must be one of {list(cfg['soil_types'])}, got {soil!r}")
    fc, pwp = cfg["soil_types"][soil]["fc"], cfg["soil_types"][soil]["pwp"]
    trigger = fc - cfg["depletion_fraction_p"] * (fc - pwp)
    return {"soil": soil, "fc": fc, "pwp": pwp, "trigger": round(trigger, 2)}


def stage_for_days(days_after_transplanting: int, cfg: dict | None = None) -> str:
    """Map days after transplanting to a tomato growth stage using `stage_max_days`."""
    cfg = cfg or load_agronomy()
    for stage, max_days in cfg["stage_max_days"].items():
        if days_after_transplanting <= max_days:
            return stage
    return list(cfg["stage_max_days"])[-1]
