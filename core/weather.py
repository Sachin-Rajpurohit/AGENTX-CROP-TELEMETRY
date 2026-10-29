"""Weather risk lookup via Open-Meteo with disk cache and fallback fixture.

Never raises on network failure: returns a ``WeatherRisk`` with
``source='fallback'`` so the caller can lower confidence accordingly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from core import schema

DEFAULT_LAT = 10.79
DEFAULT_LON = 78.70
DEFAULT_DAYS = 5
TIMEOUT_S = 5
CACHE_TTL_S = 3600  # 1 hour

_OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&daily=precipitation_sum,precipitation_probability_max,temperature_2m_max"
    "&forecast_days={days}&timezone=auto"
)

# Fallback fixture (dry, conservative) used when the API is unreachable.
_FALLBACK = {
    "precipitation_sum": [0.0, 0.0, 0.0, 0.0, 0.0],
    "precipitation_probability_max": [10, 10, 10, 10, 10],
    "temperature_2m_max": [33.0, 34.0, 33.0, 32.0, 32.0],
}


def _cache_path(cache_dir: str | Path, lat: float, lon: float) -> Path:
    d = Path(cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"weather_{lat:.4f}_{lon:.4f}.json"


def _read_cache(path: Path) -> dict | None:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        if time.time() - data.get("_fetched_at", 0) > CACHE_TTL_S:
            return None
        return data
    except Exception:  # noqa: BLE001 — intentional fallback on any cache read failure
        return None

def _write_cache(path: Path, data: dict) -> None:
    try:
        data["_fetched_at"] = time.time()
        path.write_text(json.dumps(data))
    except Exception:  # noqa: BLE001, S110 — intentional silent cache write failure
        pass


def get_weather_risk(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    days: int = DEFAULT_DAYS,
    cache_dir: str | Path = ".cache/weather",
) -> schema.WeatherRisk:
    """Fetch 5-day weather risk for a location.

    Returns ``source='live'`` on success, ``source='cache'`` when served from
    disk cache, or ``source='fallback'`` with a dry conservative fixture when
    the API is unreachable.  A fallback source must lower confidence downstream.
    """
    path = _cache_path(cache_dir, lat, lon)
    cached = _read_cache(path)
    if cached is not None:
        return _build_risk(cached, "cache")

    try:
        url = _OPEN_METEO_URL.format(lat=lat, lon=lon, days=days)
        resp = requests.get(url, timeout=TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
        daily = payload.get("daily", {})
        _write_cache(path, daily)
        return _build_risk(daily, "live")
    except Exception:  # noqa: BLE001 — intentional fallback on any API failure
        return _build_risk(_FALLBACK, "fallback")


def _build_risk(daily: dict, source: str) -> schema.WeatherRisk:
    p_sum = list(daily.get("precipitation_sum", [0.0]))[:days_if_present(daily)]
    p_prob = list(daily.get("precipitation_probability_max", [0.0]))[:days_if_present(daily)]
    tmax = list(daily.get("temperature_2m_max", [0.0]))[:days_if_present(daily)]

    n = max(len(p_sum), len(p_prob), len(tmax))
    # Pad short arrays.
    p_sum += [0.0] * (n - len(p_sum))
    p_prob += [0.0] * (n - len(p_prob))
    tmax += [0.0] * (n - len(tmax))

    rain_mm_48h = float(p_sum[0]) + float(p_sum[1]) if n >= 2 else float(p_sum[0]) if n == 1 else 0.0
    rain_prob_48h = max(float(p_prob[0]), float(p_prob[1])) if n >= 2 else (float(p_prob[0]) if n == 1 else 0.0)
    tmax_next3 = max(float(v) for v in tmax[:3]) if tmax else 0.0

    return schema.WeatherRisk(
        rain_mm_48h=rain_mm_48h,
        rain_prob_48h=rain_prob_48h,
        tmax_next3=tmax_next3,
        source=source,
    )


def days_if_present(daily: dict) -> int:
    """Number of forecast days actually returned by the API."""
    lengths = [
        len(daily.get(k, []))
        for k in ("precipitation_sum", "precipitation_probability_max", "temperature_2m_max")
    ]
    return max(lengths) if lengths else 0
