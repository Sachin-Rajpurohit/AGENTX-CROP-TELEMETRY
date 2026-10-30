"""The farm the current agent run is about. Set by the API for one request; unset for the CLI.

Tools read the farm's own sensor file and use its crop, area, soil, watering method and
location as defaults when the agent does not pass them explicitly.
"""
from __future__ import annotations

import os
from contextvars import ContextVar

FARM: ContextVar[dict | None] = ContextVar("farm", default=None)


def current_farm() -> dict | None:
    return FARM.get()


def telemetry_file(data_dir: str) -> str:
    """The active farm's sensor CSV, else soil_telemetry.csv in the data folder."""
    farm = FARM.get()
    return farm["telemetry_path"] if farm else os.path.join(data_dir, "soil_telemetry.csv")


def farm_default(key: str, explicit=None, fallback=None):
    """explicit argument -> active farm's value -> fallback."""
    if explicit not in (None, ""):
        return explicit
    farm = FARM.get()
    if farm and farm.get(key) not in (None, ""):
        return farm[key]
    return fallback
