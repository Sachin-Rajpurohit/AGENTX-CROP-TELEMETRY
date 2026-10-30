"""Farm storage: one JSON file of farms plus one sensor CSV per farm.

Lives in AGENTX_FARM_DIR (default .farmdata/, git-ignored). On first use it creates a demo
farm from data/soil_telemetry.csv so the app works out of the box.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import DATA_DIR
from core.quality import _resolve_column

FARM_DIR = Path(os.environ.get("AGENTX_FARM_DIR", Path(__file__).parent / ".farmdata"))
TELEMETRY_NAME = "soil_telemetry.csv"
MAX_CSV_BYTES = 2 * 1024 * 1024
_lock = threading.Lock()

DEMO_FARM = {
    "name": "Demo tomato plot",
    "crop": "tomato",
    "stage": None,
    "area_acres": 1.0,
    "irrigation": "drip",
    "soil": "clay_loam",
    "location": {"name": "Tiruchirappalli, Tamil Nadu, India", "lat": 10.79, "lon": 78.70},
}


class FarmError(ValueError):
    """Bad farm input or unusable sensor file (shown to the user)."""


def _index_path() -> Path:
    return FARM_DIR / "farms.json"


def _read() -> list[dict]:
    if not _index_path().exists():
        _seed()
    return json.loads(_index_path().read_text(encoding="utf-8"))["farms"]


def _write(farms: list[dict]) -> None:
    FARM_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _index_path().with_suffix(".tmp")
    tmp.write_text(json.dumps({"farms": farms}, indent=2), encoding="utf-8")
    tmp.replace(_index_path())


def _seed() -> None:
    farm = {**DEMO_FARM, "id": uuid.uuid4().hex[:8], "created_at": _now()}
    farm_dir = FARM_DIR / farm["id"]
    farm_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(DATA_DIR) / TELEMETRY_NAME, farm_dir / TELEMETRY_NAME)
    _write([farm])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: UP017 - datetime.UTC needs Python 3.11


def telemetry_path(farm_id: str) -> Path:
    return FARM_DIR / farm_id / TELEMETRY_NAME


def _public(farm: dict) -> dict:
    return {**farm, "has_telemetry": telemetry_path(farm["id"]).exists()}


def list_farms() -> list[dict]:
    with _lock:
        return [_public(f) for f in _read()]


def get_farm(farm_id: str) -> dict:
    with _lock:
        for f in _read():
            if f["id"] == farm_id:
                return _public(f)
    raise KeyError(farm_id)


def create_farm(data: dict) -> dict:
    with _lock:
        farms = _read()
        farm = {**data, "id": uuid.uuid4().hex[:8], "created_at": _now()}
        _write([*farms, farm])
        return _public(farm)


def update_farm(farm_id: str, data: dict) -> dict:
    with _lock:
        farms = _read()
        for i, f in enumerate(farms):
            if f["id"] == farm_id:
                farms[i] = {**f, **data, "id": farm_id}
                _write(farms)
                return _public(farms[i])
    raise KeyError(farm_id)


def delete_farm(farm_id: str) -> None:
    with _lock:
        farms = _read()
        if not any(f["id"] == farm_id for f in farms):
            raise KeyError(farm_id)
        _write([f for f in farms if f["id"] != farm_id])
        shutil.rmtree(FARM_DIR / farm_id, ignore_errors=True)


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    """Parse an uploaded sensor CSV; it must have a numeric moisture column."""
    if len(data) > MAX_CSV_BYTES:
        raise FarmError(f"CSV larger than {MAX_CSV_BYTES // (1024 * 1024)} MB")
    try:
        df = pd.read_csv(io.BytesIO(data))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise FarmError(f"could not parse CSV: {e}") from e
    col = _resolve_column(df, "moisture")
    if df.empty or col is None or pd.to_numeric(df[col], errors="coerce").dropna().empty:
        raise FarmError("CSV needs at least one row with a numeric 'moisture' column")
    return df


def save_telemetry(farm_id: str, data: bytes) -> pd.DataFrame:
    get_farm(farm_id)  # raises KeyError for an unknown farm
    df = read_csv_bytes(data)
    path = telemetry_path(farm_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return df


def load_telemetry(farm_id: str) -> pd.DataFrame | None:
    path = telemetry_path(farm_id)
    return pd.read_csv(path) if path.exists() else None
