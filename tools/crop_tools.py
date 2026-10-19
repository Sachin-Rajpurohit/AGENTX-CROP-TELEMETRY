"""Crop advisory tools for the AgentX starter. Every tool returns a JSON string and never raises."""
import json
import os
import time

import numpy as np
import pandas as pd
import requests

from tools import Tool

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE = os.path.join(REPO_ROOT, "knowledge", "crop_requirements.json")


def _data_dir():
    """Read AGENTX_DATA_DIR at call time so tests and the judges' harness can change it."""
    return os.environ.get("AGENTX_DATA_DIR") or os.path.join(REPO_ROOT, "data")

# Assumptions used by calculate_dosage. They are reported in every result. Replace with TNAU/ICAR values.
ROOT_ZONE_MM = 300            # assumed root-zone depth for the water calculation
ACRES_PER_HECTARE = 2.471
MAX_NUTRIENT_KG_PER_ACRE = 60  # guardrail cap per nutrient
MAX_WATER_MM = 25              # guardrail cap per irrigation
LITRES_PER_MM_PER_ACRE = 4046.86

ALIASES = {"moisture": ["moisture", "soil_moisture", "soilmoisture"], "N": ["n", "nitrogen"],
           "P": ["p", "phosphorus", "phosphorous"], "K": ["k", "potassium"], "pH": ["ph"],
           "temperature": ["temperature", "temp"], "rainfall": ["rainfall", "rain"],
           "humidity": ["humidity"], "crop": ["crop", "label"],
           "time": ["timestamp", "time", "date", "datetime"]}
NUTRIENTS = ["N", "P", "K"]


def _out(d):
    return json.dumps(d, default=str)


def _load():
    try:
        df = pd.read_csv(os.path.join(_data_dir(), "soil_telemetry.csv"))
    except pd.errors.EmptyDataError:
        raise ValueError("soil_telemetry.csv is empty")
    if df.empty:
        raise ValueError("soil_telemetry.csv is empty")
    lower = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for std, names in ALIASES.items():
        for n in names:
            if n in lower:
                rename[lower[n]] = std
                break
    df = df.rename(columns=rename)
    if "time" in df:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time")
    return df


def _window(df, days):
    if "time" in df:
        return df[df["time"] >= df["time"].max() - pd.Timedelta(days=days)]
    return df.tail(days)          # no time column: treat the last N rows as N readings


def _int(v, default):
    try:
        return int(float(v))
    except Exception:
        return default


def _num(v, default):
    try:
        return float(v)
    except Exception:
        return default


class GetSoilReadings(Tool):
    name = "get_soil_readings"
    description = "Summarise recent soil sensor data (mean and latest value per column) from soil_telemetry.csv."
    args_doc = '{"days": 7}'

    def execute(self, days=7, **kw):
        try:
            df = _window(_load(), _int(days, 7))
            num = df.select_dtypes("number")
            if num.empty:
                return _out({"error": "no numeric columns in soil data"})
            res = {"rows": len(df), "has_time_column": "time" in df, "columns": list(num.columns),
                   "mean": num.mean().round(2).to_dict(), "latest": num.iloc[-1].round(2).to_dict()}
            if "crop" in df:
                res["crops_in_data"] = df["crop"].dropna().astype(str).unique().tolist()[:10]
            return _out(res)
        except Exception as e:
            return _out({"error": f"could not read soil data: {e}"})


class AnalyzeTrend(Tool):
    name = "analyze_trend"
    description = ("Trend of one soil column over the data (slope, min, max, status falling/rising/stable). "
                   "Columns: moisture, N, P, K, pH, temperature, rainfall.")
    args_doc = '{"column": "moisture", "days": 7}'

    def execute(self, column="moisture", days=7, **kw):
        try:
            df = _window(_load(), _int(days, 7))
            if column not in df:
                return _out({"error": f"column '{column}' not found. Available: {list(df.columns)}"})
            y = pd.to_numeric(df[column], errors="coerce").dropna().to_numpy()
            if len(y) < 3:
                return _out({"error": f"only {len(y)} readings. Need at least 3 to judge a trend."})
            slope = float(np.polyfit(range(len(y)), y, 1)[0])
            status = "falling" if slope < -0.05 else "rising" if slope > 0.05 else "stable"
            return _out({"column": column, "readings": len(y), "slope_per_reading": round(slope, 3),
                         "min": float(y.min()), "max": float(y.max()), "latest": float(y[-1]), "status": status})
        except Exception as e:
            return _out({"error": f"trend failed: {e}"})


class WeatherForecast(Tool):
    name = "get_weather_forecast"
    description = "3-day rain probability (%) and rainfall (mm) from Open-Meteo. Defaults to Tiruchirappalli."
    args_doc = '{"lat": 10.79, "lon": 78.70}'

    def execute(self, lat=10.79, lon=78.70, **kw):
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
               "&daily=precipitation_sum,precipitation_probability_max&forecast_days=3"
               % (_num(lat, 10.79), _num(lon, 78.70)))
        for _ in range(2):        # retry once
            try:
                d = requests.get(url, timeout=5).json()["daily"]
                return _out({"rain_probability_pct": d["precipitation_probability_max"],
                             "rain_mm": d["precipitation_sum"], "days_ahead": [1, 2, 3]})
            except Exception:
                time.sleep(1)
        return _out({"error": "weather forecast unavailable after retry. Advise conservatively and say so."})


def _requirements(crop, stage=None):
    with open(KNOWLEDGE) as f:
        table = json.load(f)
    key = {k.lower(): k for k in table}.get(str(crop).lower().strip())
    if key is None:
        return None, sorted(table)
    entry = table[key]
    vals = dict(entry.get("ideal", {}))
    used_stage = None
    if stage and stage in entry.get("stages", {}):
        vals.update(entry["stages"][stage])
        used_stage = stage
    return {"crop": key, "stage": used_stage, "ideal": vals, "source": entry.get("source", "unknown")}, sorted(table)


class CropRequirements(Tool):
    name = "get_crop_requirements"
    description = "Ideal soil values (N, P, K, pH, moisture, rainfall where known) for a crop, optionally by growth stage."
    args_doc = '{"crop": "tomato", "stage": "flowering"}'

    def execute(self, crop="tomato", stage=None, **kw):
        try:
            res, known = _requirements(crop, stage)
            if res is None:
                return _out({"error": f"no requirements for '{crop}'", "known_crops": known})
            return _out(res)
        except Exception as e:
            return _out({"error": f"could not read crop requirements: {e}"})


class CalculateDosage(Tool):
    name = "calculate_dosage"
    description = ("Fertilizer (N, P, K kg) and irrigation (mm, litres) needed to close the gap between the latest soil "
                   "readings and the crop's ideal values, for a given area. Capped for safety.")
    args_doc = '{"crop": "tomato", "area_acres": 1.0, "stage": "flowering"}'

    def execute(self, crop="tomato", area_acres=1.0, stage=None, **kw):
        try:
            area = _num(area_acres, 1.0)
            if area <= 0:
                return _out({"error": "area_acres must be positive"})
            req, known = _requirements(crop, stage)
            if req is None:
                return _out({"error": f"no requirements for '{crop}'", "known_crops": known})
            df = _window(_load(), 7)
            if len(df) < 3:
                return _out({"error": f"only {len(df)} readings. Refusing to calculate a dosage."})
            latest = df.select_dtypes("number").iloc[-1]
            ideal, out, notes = req["ideal"], {}, []
            for n in NUTRIENTS:
                if n in ideal and n in latest.index:
                    deficit = max(float(ideal[n]) - float(latest[n]), 0.0)
                    kg = deficit / ACRES_PER_HECTARE * area   # assumes N/P/K are kg/ha-equivalent
                    capped = min(kg, MAX_NUTRIENT_KG_PER_ACRE * area)
                    out[n] = {"current": round(float(latest[n]), 2), "ideal": ideal[n],
                              "deficit": round(deficit, 2), "dose_kg": round(capped, 2)}
                    if capped < kg:
                        notes.append(f"{n} dose capped at {MAX_NUTRIENT_KG_PER_ACRE} kg/acre")
            if "moisture" in ideal and "moisture" in latest.index:
                deficit = max(float(ideal["moisture"]) - float(latest["moisture"]), 0.0)
                mm = min(deficit / 100.0 * ROOT_ZONE_MM, MAX_WATER_MM)
                out["water"] = {"current_pct": round(float(latest["moisture"]), 2), "ideal_pct": ideal["moisture"],
                                "irrigation_mm": round(mm, 1), "litres": round(mm * LITRES_PER_MM_PER_ACRE * area)}
            if not out:
                return _out({"error": "no overlapping columns between soil data and crop requirements",
                             "soil_columns": list(latest.index), "ideal_keys": list(ideal)})
            return _out({"crop": req["crop"], "stage": req["stage"], "area_acres": area, "dosage": out, "notes": notes,
                         "assumptions": (f"N/P/K read as kg/ha-equivalent, root zone {ROOT_ZONE_MM} mm. "
                                         "Estimate only. Confirm with a local agriculture officer."),
                         "requirements_source": req["source"]})
        except Exception as e:
            return _out({"error": f"dosage failed: {e}"})


CROP_TOOLS = [GetSoilReadings, AnalyzeTrend, WeatherForecast, CropRequirements, CalculateDosage]