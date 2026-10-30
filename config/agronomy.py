"""Loader for config/agronomy.yaml. Every agronomy constant lives in the YAML, not in code."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

AGRONOMY_YAML = Path(__file__).with_name("agronomy.yaml")
WHOLE_SEASON = "whole_season"


@lru_cache(maxsize=1)
def load_agronomy() -> dict:
    with open(AGRONOMY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_crop(crop: str | None = None, cfg: dict | None = None) -> str:
    """Normalise a crop name ("Paddy" -> "rice") and check it is supported."""
    cfg = cfg or load_agronomy()
    crop = (crop or cfg["default_crop"]).strip().lower()
    crop = {"paddy": "rice", "corn": "maize"}.get(crop, crop)
    if crop not in cfg["crops"]:
        raise ValueError(f"crop must be one of {list(cfg['crops'])}, got {crop!r}")
    return crop


def moisture_thresholds(soil: str | None = None, cfg: dict | None = None, crop: str | None = None) -> dict:
    """FC, PWP and irrigation trigger (volumetric %) for a soil type and crop.

    Dry-land crops use the FAO-56 trigger FC - p * (FC - PWP). Flooded rice is re-irrigated
    once ponded water is gone, approximated as moisture below FC."""
    cfg = cfg or load_agronomy()
    crop = resolve_crop(crop, cfg)
    soil = soil or cfg["default_soil"]
    if soil not in cfg["soil_types"]:
        raise ValueError(f"soil must be one of {list(cfg['soil_types'])}, got {soil!r}")
    fc, pwp = cfg["soil_types"][soil]["fc"], cfg["soil_types"][soil]["pwp"]
    crop_cfg = cfg["crops"][crop]
    trigger = fc if crop_cfg.get("flooded") else fc - crop_cfg["p"] * (fc - pwp)
    return {"crop": crop, "soil": soil, "fc": fc, "pwp": pwp, "trigger": round(trigger, 2)}


def crop_stages(crop: str, cfg: dict | None = None) -> list[str]:
    """Growth stages with their own targets; empty when the crop has one whole-season target."""
    cfg = cfg or load_agronomy()
    return list(cfg["crops"][resolve_crop(crop, cfg)].get("stages", {}))


def stage_for_days(days: int, crop: str | None = None, cfg: dict | None = None) -> str:
    """Map days after transplanting/sowing to a growth stage using each stage's `max_days`."""
    cfg = cfg or load_agronomy()
    stages = cfg["crops"][resolve_crop(crop, cfg)].get("stages")
    if not stages:
        return WHOLE_SEASON
    for stage, values in stages.items():
        if days <= values["max_days"]:
            return stage
    return list(stages)[-1]


def stage_requirement(crop: str, stage: str | None, days: int, cfg: dict | None = None) -> tuple[str, dict]:
    """(stage label, {"N","P","K"} kg/ha). `stage` overrides the stage derived from `days`;
    crops without stage data ignore it and use the whole-season target."""
    cfg = cfg or load_agronomy()
    crop_cfg = cfg["crops"][resolve_crop(crop, cfg)]
    stages = crop_cfg.get("stages")
    if not stages:
        return WHOLE_SEASON, {n: crop_cfg["targets"][n] for n in ("N", "P", "K")}
    if stage is not None and stage not in stages:
        raise ValueError(f"stage for {crop} must be one of {list(stages)}, got {stage!r}")
    stage = stage or stage_for_days(days, crop, cfg)
    return stage, {n: stages[stage][n] for n in ("N", "P", "K")}
