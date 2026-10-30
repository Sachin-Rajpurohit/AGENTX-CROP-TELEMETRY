"""Crop advisory tools for the AgentX starter. Every tool returns a JSON string and never raises."""
import csv
import json
import os

from tools import Tool
from tools.farm_context import current_farm, farm_default, telemetry_file

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    filepath = telemetry_file(_data_dir())
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
                   "Columns: moisture, N, P, K, pH, temperature, rainfall. For moisture, also the crop's "
                   "irrigation trigger.")
    args_doc = '{"column": "moisture", "days": 7, "crop": "tomato"}'

    def execute(self, column="moisture", days=7, crop=None, **kw):
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
                try:
                    t = moisture_thresholds(soil=farm_default("soil"), crop=farm_default("crop", crop))
                    res["thresholds"] = t
                    res["below_trigger"] = vals[-1] < t["trigger"]
                except ValueError as e:
                    res["thresholds_note"] = str(e)
            return _out(res)
        except Exception as e:
            return _out({"error": f"trend failed: {e}"})


class WeatherForecast(Tool):
    name = "get_weather_forecast"
    description = ("48-hour rain (mm, max probability %) and next-3-day max temperature from Open-Meteo. "
                   "Defaults to Tiruchirappalli. source='fallback' means the live forecast was unavailable.")
    args_doc = '{} (optional "lat", "lon"; default: the selected farm\'s location)'

    def execute(self, lat=None, lon=None, **kw):
        from dataclasses import asdict

        from core.weather import get_weather_risk
        lat, lon = _num(farm_default("lat", lat, 10.79), 10.79), _num(farm_default("lon", lon, 78.70), 78.70)
        risk = {**asdict(get_weather_risk(lat, lon)), "lat": lat, "lon": lon}
        if risk["source"] == "fallback":
            risk["note"] = "Live forecast unavailable; this is a dry fallback. Advise conservatively and say so."
        return _out(risk)


class CropRequirements(Tool):
    name = "get_crop_requirements"
    description = ("N/P/K targets (kg/ha), growth stages and irrigation trigger for any of the 23 supported crops, "
                   "and where the targets come from.")
    args_doc = '{"crop": "tomato", "stage": "flowering"}'

    def execute(self, crop=None, stage=None, **kw):
        try:
            from config.agronomy import (
                crop_stages,
                load_agronomy,
                moisture_thresholds,
                resolve_crop,
                stage_requirement,
                targets_from_dataset,
            )
            try:
                crop = resolve_crop(farm_default("crop", crop))
            except ValueError:
                return _out({"error": f"no requirements for '{crop}'",
                             "supported_crops": sorted(load_agronomy()["crops"])})
            stages = crop_stages(crop)
            label, targets = stage_requirement(crop, stage if stage in stages else None, 30)
            return _out({
                "crop": crop,
                "stage": label,
                "stages": stages,
                "targets_kg_ha": targets,
                "targets_source": ("median of this crop's rows in the Kaggle Crop Recommendation dataset"
                                   if targets_from_dataset(crop) else "TNAU Agritech Portal & ICAR"),
                "moisture_thresholds": moisture_thresholds(soil=farm_default("soil"), crop=crop),
            })
        except Exception as e:
            return _out({"error": f"could not read crop requirements: {e}"})


class CalculateDosage(Tool):
    name = "calculate_dosage"
    description = ("Full advisory from soil_telemetry.csv: decision, urgency, irrigation litres/day and fertilizer "
                   "kg (urea, DAP, MOP) for the area, using the live 48h forecast, sensor quality checks and safety "
                   "rules. 23 crops: tomato (stages seedling, vegetative, flowering, fruiting), rice (seedling, "
                   "tillering, flowering, ripening; always flooded), and whole-season targets (stage ignored) for "
                   "maize, cotton, apple, banana, blackgram, chickpea, coconut, coffee, grapes, jute, kidneybeans, "
                   "lentil, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, "
                   "watermelon. Omit stage if unknown. Irrigation: drip or flood.")
    args_doc = ('{"crop": "tomato", "area_acres": 1.0, "stage": "flowering", "irrigation": "drip"} '
                '(all optional: omitted values come from the selected farm)')

    def execute(self, crop=None, area_acres=None, stage=None, irrigation=None, soil=None, lat=None, lon=None, **kw):
        try:
            import pandas as pd

            from agent.advisor import run_advisory
            from config.agronomy import load_agronomy, resolve_crop
            farm = current_farm() or {}
            try:
                crop = resolve_crop(farm_default("crop", crop))
            except ValueError:
                return _out({"error": f"no dose model for '{crop}'. Supported: {list(load_agronomy()['crops'])}. "
                                      "Use check_crop_suitability and give general advice, saying so."})
            df = pd.read_csv(telemetry_file(_data_dir()))
            if len(df) < 3:
                return _out({"error": f"only {len(df)} readings. Refusing to calculate a dosage."})
            # The farm's saved stage only applies when the question is about the farm's own crop.
            stage = stage or (farm.get("stage") if farm.get("crop") == crop else None)
            area_acres = _num(farm_default("area_acres", area_acres, 1.0), 1.0)
            r = run_advisory(df, area_acres=area_acres,
                             irrigation=str(farm_default("irrigation", irrigation, "drip")).lower(),
                             days_after_transplanting=int(farm_default("days_after_transplanting", None, 30)),
                             lat=_num(farm_default("lat", lat, 10.79), 10.79),
                             lon=_num(farm_default("lon", lon, 78.70), 78.70),
                             crop=crop, soil=farm_default("soil", soil), stage=stage or None)
            doses = r["doses"] or {}
            fert = doses.get("fertilizer")
            water = doses.get("irrigation")
            return _out({
                "answer_draft": r["answer"],
                "decision": r["decision"],
                "urgency": r["urgency"],
                "why": r["reasons"],
                "crop": r["crop"],
                "stage": r["stage"],
                "area_acres": area_acres,
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


class CheckCropSuitability(Tool):
    name = "check_crop_suitability"
    description = ("Which of 22 crops (Kaggle Crop Recommendation dataset) best suit the latest soil N, P, K, pH, "
                   "temperature and humidity in soil_telemetry.csv, and how well a named crop fits. "
                   "Use for 'what should I grow' or crops without a dose model.")
    args_doc = '{"crop": "rice"}'

    def execute(self, crop=None, **kw):
        try:
            import pandas as pd

            from core.crop_fit import crop_fit
            df = pd.read_csv(telemetry_file(_data_dir()))
            cols = {c.lower(): c for c in df.columns}

            def latest(name):
                col = cols.get(name.lower())
                vals = pd.to_numeric(df[col], errors="coerce").dropna() if col else []
                return float(vals.iloc[-1]) if len(vals) else None

            readings = {f: latest(f) for f in ("N", "P", "K", "temperature", "humidity", "ph")}
            return _out(crop_fit(readings, crop=farm_default("crop", crop)))
        except Exception as e:
            return _out({"error": f"crop suitability failed: {e}"})


CROP_TOOLS = [GetSoilReadings, AnalyzeTrend, WeatherForecast, CropRequirements, CalculateDosage,
              CheckCropSuitability]
