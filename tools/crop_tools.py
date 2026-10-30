"""Crop advisory tools for the AgentX starter. Every tool returns a JSON string and never raises."""
import csv
import json
import os
import re
import time
import urllib.request
import urllib.error

from tools import Tool

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _knowledge_path():
    p1 = os.path.join(REPO_ROOT, "knowledge", "crop_requirements.json")
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(_data_dir(), "crop_requirements.json")
    if os.path.exists(p2):
        return p2
    return os.path.join(REPO_ROOT, "data", "crop_requirements.json")


def _data_dir():
    """Read AGENTX_DATA_DIR at call time so tests and the judges' harness can change it."""
    return os.environ.get("AGENTX_DATA_DIR") or os.path.join(REPO_ROOT, "data")


# Assumptions used by calculate_dosage. Reported in every result.
ROOT_ZONE_MM = 300            # assumed root-zone depth for the water calculation
ACRES_PER_HECTARE = 2.471
MAX_NUTRIENT_KG_PER_ACRE = 60  # guardrail cap per nutrient
MAX_WATER_MM = 25              # guardrail cap per irrigation
LITRES_PER_MM_PER_ACRE = 4046.86

ALIASES = {
    "moisture": ["moisture", "soil_moisture", "soilmoisture"],
    "N": ["n", "nitrogen"],
    "P": ["p", "phosphorus", "phosphorous"],
    "K": ["k", "potassium"],
    "pH": ["ph"],
    "temperature": ["temperature", "temp"],
    "rainfall": ["rainfall", "rain"],
    "humidity": ["humidity"],
    "crop": ["crop", "label"],
    "time": ["timestamp", "time", "date", "datetime"]
}
NUTRIENTS = ["N", "P", "K"]


def _out(d):
    return json.dumps(d, default=str)


def _load_rows():
    """Load soil_telemetry.csv using stdlib csv with alias mapping."""
    filepath = os.path.join(_data_dir(), "soil_telemetry.csv")
    if not os.path.exists(filepath):
        raise ValueError("soil_telemetry.csv not found")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = list(csv.reader(f))
    if len(reader) < 2:
        raise ValueError("soil_telemetry.csv is empty")

    raw_header = [h.strip() for h in reader[0]]
    col_map = {}
    for std, names in ALIASES.items():
        for i, h in enumerate(raw_header):
            hl = h.lower()
            if hl in names:
                col_map[std] = i
                break

    rows = []
    for r in reader[1:]:
        if not any(r):
            continue
        entry = {}
        for std, idx in col_map.items():
            if idx < len(r):
                entry[std] = r[idx].strip()
        rows.append(entry)
    if not rows:
        raise ValueError("soil_telemetry.csv is empty")
    return rows, list(col_map.keys())


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
            rows, cols = _load_rows()
            w = rows[-_int(days, 7):] if len(rows) > _int(days, 7) else rows
            num_cols = ["moisture", "N", "P", "K", "pH", "temperature", "humidity", "rainfall"]
            found_num = [c for c in num_cols if any(c in r for r in w)]
            if not found_num:
                return _out({"error": "no numeric columns in soil data"})

            mean, latest = {}, {}
            for c in found_num:
                vals = []
                for r in w:
                    try:
                        vals.append(float(r[c]))
                    except (KeyError, ValueError):
                        pass
                if vals:
                    mean[c] = round(sum(vals) / len(vals), 2)
                    latest[c] = round(vals[-1], 2)

            res = {
                "rows": len(w),
                "has_time_column": any("time" in r for r in w),
                "columns": found_num,
                "mean": mean,
                "latest": latest
            }
            crops = list(set(r["crop"] for r in w if "crop" in r and r["crop"]))
            if crops:
                res["crops_in_data"] = crops[:10]
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
            rows, cols = _load_rows()
            w = rows[-_int(days, 7):] if len(rows) > _int(days, 7) else rows
            vals = []
            for r in w:
                if column in r:
                    try:
                        vals.append(float(r[column]))
                    except ValueError:
                        pass
            if not vals:
                return _out({"error": f"column '{column}' not found. Available: {cols}"})
            if len(vals) < 3:
                return _out({"error": f"only {len(vals)} readings. Need at least 3 to judge a trend."})

            # Linear regression: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
            n = len(vals)
            x = list(range(n))
            sum_x = sum(x)
            sum_y = sum(vals)
            sum_xy = sum(i * v for i, v in zip(x, vals))
            sum_xx = sum(i * i for i in x)
            denom = n * sum_xx - sum_x * sum_x
            slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0.0

            status = "falling" if slope < -0.05 else "rising" if slope > 0.05 else "stable"
            res = {
                "column": column,
                "readings": n,
                "slope_per_reading": round(slope, 3),
                "min": float(min(vals)),
                "max": float(max(vals)),
                "latest": float(vals[-1]),
                "status": status
            }
            if column == "moisture":
                from config.agronomy import moisture_thresholds
                t = moisture_thresholds()
                res["thresholds"] = t
                res["below_trigger"] = vals[-1] < t["trigger"]
            return _out(res)
        except Exception as e:
            return _out({"error": f"trend failed: {e}"})


class WeatherForecast(Tool):
    name = "get_weather_forecast"
    description = ("48-hour rain (mm, max probability %) and next-3-day max temperature from Open-Meteo. "
                   "Defaults to Tiruchirappalli. source='fallback' means the live forecast was unavailable.")
    args_doc = '{"lat": 10.79, "lon": 78.70}'

    def execute(self, lat=10.79, lon=78.70, **kw):
        from dataclasses import asdict

        from core.weather import get_weather_risk
        risk = asdict(get_weather_risk(_num(lat, 10.79), _num(lon, 78.70)))
        if risk["source"] == "fallback":
            risk["note"] = "Live forecast unavailable; this is a dry fallback. Advise conservatively and say so."
        return _out(risk)


def _requirements(crop, stage=None):
    kpath = _knowledge_path()
    if not os.path.exists(kpath):
        return None, []
    with open(kpath, "r", encoding="utf-8") as f:
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
            if res["crop"] == "tomato":
                from config.agronomy import moisture_thresholds
                res["ideal"].pop("moisture", None)
                res["moisture_thresholds"] = moisture_thresholds()
            return _out(res)
        except Exception as e:
            return _out({"error": f"could not read crop requirements: {e}"})


class CalculateDosage(Tool):
    name = "calculate_dosage"
    description = ("Full advisory for tomato from soil_telemetry.csv: decision, urgency, irrigation litres/day and "
                   "fertilizer kg (urea, DAP, MOP) for the area, using the live 48h forecast, sensor quality checks "
                   "and safety rules. Stages: seedling, vegetative, flowering, fruiting. Irrigation: drip or flood.")
    args_doc = '{"crop": "tomato", "area_acres": 1.0, "stage": "flowering", "irrigation": "drip"}'

    def execute(self, crop="tomato", area_acres=1.0, stage=None, irrigation="drip", lat=10.79, lon=78.70, **kw):
        try:
            import pandas as pd

            from agent.advisor import run_advisory
            if str(crop).lower().strip() != "tomato":
                return _out({"error": f"dosage model is calibrated for tomato only, not '{crop}'. "
                                      "Give general advice and say so."})
            df = pd.read_csv(os.path.join(_data_dir(), "soil_telemetry.csv"))
            if len(df) < 3:
                return _out({"error": f"only {len(df)} readings. Refusing to calculate a dosage."})
            r = run_advisory(df, area_acres=_num(area_acres, 1.0), irrigation=str(irrigation).lower(),
                             days_after_transplanting=30, lat=_num(lat, 10.79), lon=_num(lon, 78.70),
                             stage=stage or "vegetative")
            doses = r["doses"] or {}
            fert = doses.get("fertilizer")
            water = doses.get("irrigation")
            return _out({
                "answer_draft": r["answer"],
                "decision": r["decision"],
                "urgency": r["urgency"],
                "why": r["reasons"],
                "stage": r["stage"],
                "area_acres": _num(area_acres, 1.0),
                "moisture_now_pct": r["readings"]["moisture"],
                "moisture_thresholds": r["moisture_thresholds"],
                "water": water and {
                    "litres_today": round(water["litres_per_day"]),
                    "sessions_today": water["events_per_day"],
                    "days_to_refill": water["days_to_refill"],
                    "method": doses["method"],
                },
                "fertilizer_kg_for_area": fert and {
                    "urea": fert["kg_area"]["urea_net"],
                    "dap": fert["kg_area"]["dap"],
                    "mop": fert["kg_area"]["mop"],
                },
                "weather": r["weather"],
                "confidence": r["confidence"],
                "assumptions": r["assumptions"],
            })
        except Exception as e:
            return _out({"error": f"dosage failed: {e}"})


CROP_TOOLS = [GetSoilReadings, AnalyzeTrend, WeatherForecast, CropRequirements, CalculateDosage]
