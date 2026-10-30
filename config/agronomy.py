"""Loader for config/agronomy.yaml. Every agronomy constant lives in the YAML, not in code."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

AGRONOMY_YAML = Path(__file__).with_name("agronomy.yaml")
WHOLE_SEASON = "whole_season"


@lru_cache(maxsize=1)
def load_agronomy() -> dict:
    with open(AGRONOMY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


ALIASES = {"paddy": "rice", "corn": "maize", "urad": "blackgram", "toor": "pigeonpeas", "arhar": "pigeonpeas",
           "rajma": "kidneybeans", "moong": "mungbean", "greengram": "mungbean", "chana": "chickpea",
           "bengalgram": "chickpea", "melon": "muskmelon", "grape": "grapes"}
EN_NAMES = {"blackgram": "Black gram", "kidneybeans": "Kidney beans", "mothbeans": "Moth beans",
            "mungbean": "Mung bean", "pigeonpeas": "Pigeon peas", "rice": "Rice (paddy)"}


def resolve_crop(crop: str | None = None, cfg: dict | None = None) -> str:
    """Normalise a crop name ("Paddy" -> "rice", "kidney beans" -> "kidneybeans") and check it is supported."""
    cfg = cfg or load_agronomy()
    raw = (crop or cfg["default_crop"]).strip().lower()
    key = raw.replace(" ", "").replace("-", "").replace("_", "")
    key = ALIASES.get(key, key)
    for candidate in (key, key + "s", key.removesuffix("s"), key.removesuffix("es")):
        if candidate in cfg["crops"]:
            return candidate
    raise ValueError(f"crop must be one of {sorted(cfg['crops'])}, got {raw!r}")


def crop_names(crop: str, cfg: dict | None = None) -> tuple[str, str]:
    """(English, Tamil) display names."""
    cfg = cfg or load_agronomy()
    return EN_NAMES.get(crop, crop.capitalize()), cfg["crops"][crop].get("ta", crop)


def find_crop_in_text(text: str, cfg: dict | None = None) -> str | None:
    """First supported crop mentioned in free text (English names and common Indian names)."""
    cfg = cfg or load_agronomy()
    words = re.findall(r"[a-z]+", text.lower())
    # Whole words and two-word names ("kidney beans"), so "price" never matches "rice".
    for candidate in [*words, *(a + b for a, b in zip(words, words[1:]))]:
        try:
            return resolve_crop(candidate, cfg)
        except ValueError:
            continue
    return None


def targets_from_dataset(crop: str, cfg: dict | None = None) -> bool:
    cfg = cfg or load_agronomy()
    return cfg["crops"][resolve_crop(crop, cfg)].get("targets") == "dataset"


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
        if crop_cfg["targets"] == "dataset":
            from core.crop_fit import dataset_targets
            return WHOLE_SEASON, dataset_targets(resolve_crop(crop, cfg))
        return WHOLE_SEASON, {n: crop_cfg["targets"][n] for n in ("N", "P", "K")}
    if stage is not None and stage not in stages:
        raise ValueError(f"stage for {crop} must be one of {list(stages)}, got {stage!r}")
    stage = stage or stage_for_days(days, crop, cfg)
    return stage, {n: stages[stage][n] for n in ("N", "P", "K")}
