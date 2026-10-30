"""FastAPI backend for AGENTX Crop Telemetry Sensor-to-Dose Advisor.

Run:  python server.py   (or: uvicorn server:app --port 8000)

Endpoints:
  GET  /api/health                        liveness check
  GET  /api/sample                        bundled sample telemetry CSV + default parameters
  GET  /api/crops                         supported crops, their stages and water rule
  GET  /api/crop-fit?N=..&P=..&K=..       which of 22 crops suit these soil/climate readings (Kaggle data)
  POST /api/advice                        multipart form, see api_advice() for fields
  GET  /api/voice?text=...&lang=en|ta     spoken advisory as audio/mpeg (needs gTTS + internet)
  GET  /api/weather?lat=..&lon=..         5-day forecast and 48h rain/heat risk
  POST /api/chat  {"message", "farm_id"?}  the same ReAct agent as `python main.py`, answer parsed for display
  GET  /api/geocode?q=...                 search any place by name (Open-Meteo geocoding)
  GET|POST /api/farms, GET|PUT|DELETE /api/farms/{id}      the farmer's fields
  GET|POST /api/farms/{id}/telemetry      a farm's sensor readings (POST: upload CSV)
  POST /api/farms/{id}/advice             advisory for a farm with its own data and settings
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

import farm_store
from agent.advisor import run_advisory
from agent.prompt_builder import farm_role
from config import DATA_DIR
from config.agronomy import crop_stages, load_agronomy, resolve_crop
from core.crop_fit import crop_fit
from core.dosage import IRRIGATION_METHODS
from core.weather import get_daily_forecast
from main import run_agent
from tools.farm_context import FARM

SAMPLE_CSV_PATH = Path(DATA_DIR) / "soil_telemetry.csv"
MAX_VOICE_CHARS = 1000
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

app = FastAPI(title="AGENTX Crop Telemetry", description="Sensor-to-Dose Advisor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("AGENTX_CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def _defaults() -> dict:
    cfg = load_agronomy()
    return {
        "area_acres": 1.0,
        "irrigation": "drip",
        "days_after_transplanting": 30,
        "lat": cfg["default_lat"],
        "lon": cfg["default_lon"],
        "crop": cfg["default_crop"],
        "soil": cfg["default_soil"],
        "soil_types": list(cfg["soil_types"]),
    }


def _read_csv(data: bytes) -> pd.DataFrame:
    try:
        return farm_store.read_csv_bytes(data)
    except farm_store.FarmError as e:
        raise HTTPException(400, str(e)) from e


def _rows(df: pd.DataFrame) -> list[dict]:
    """DataFrame rows as JSON-safe dicts (NaN -> null)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


def _farm_or_404(farm_id: str) -> dict:
    try:
        return farm_store.get_farm(farm_id)
    except KeyError:
        raise HTTPException(404, f"no farm with id {farm_id!r}") from None


def _farm_context(farm: dict) -> dict:
    """Flat values the agent tools read for the selected farm."""
    return {"name": farm["name"], "crop": farm["crop"], "stage": farm.get("stage"),
            "area_acres": farm["area_acres"], "irrigation": farm["irrigation"], "soil": farm["soil"],
            "lat": farm["location"]["lat"], "lon": farm["location"]["lon"],
            "telemetry_path": str(farm_store.telemetry_path(farm["id"]))}


class Location(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    crop: str
    stage: str | None = None
    area_acres: float = Field(gt=0, le=10_000)
    irrigation: str = "drip"
    soil: str = "clay_loam"
    location: Location


def _validated(body: FarmIn) -> dict:
    cfg = load_agronomy()
    try:
        crop = resolve_crop(body.crop, cfg)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    stage = body.stage or None
    if stage and stage not in crop_stages(crop, cfg):
        raise HTTPException(400, f"stage for {crop} must be one of {crop_stages(crop, cfg)}, got {stage!r}")
    irrigation = "flood" if cfg["crops"][crop].get("flooded") else body.irrigation.lower()
    if irrigation not in IRRIGATION_METHODS:
        raise HTTPException(400, f"irrigation must be one of {list(IRRIGATION_METHODS)}")
    if body.soil not in cfg["soil_types"]:
        raise HTTPException(400, f"soil must be one of {list(cfg['soil_types'])}")
    return {"name": body.name.strip(), "crop": crop, "stage": stage, "area_acres": body.area_acres,
            "irrigation": irrigation, "soil": body.soil, "location": body.location.model_dump()}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/sample")
def api_sample():
    """Bundled sample telemetry and the default form parameters."""
    rows = _rows(pd.read_csv(SAMPLE_CSV_PATH))
    return {"csv": SAMPLE_CSV_PATH.read_text(encoding="utf-8"), "rows": rows, "metadata": _defaults()}


@app.get("/api/weather")
def api_weather(lat: float | None = None, lon: float | None = None):
    """Day-by-day forecast plus which advisory rules the next 48-72 h would trigger."""
    d, cfg = _defaults(), load_agronomy()
    forecast = get_daily_forecast(d["lat"] if lat is None else lat, d["lon"] if lon is None else lon)
    risk = forecast["risk"]
    forecast["effects"] = {
        "skip_irrigation": risk["rain_mm_48h"] >= cfg["rain_skip_threshold_mm"]
        and risk["rain_prob_48h"] >= cfg["rain_skip_prob_pct"],
        "delay_fertilizer": risk["rain_mm_48h"] >= cfg["rain_delay_threshold_mm"],
        "irrigate_at_dawn": risk["tmax_next3"] >= cfg["heat_threshold_c"],
        "thresholds": {k: cfg[k] for k in ("rain_skip_threshold_mm", "rain_skip_prob_pct",
                                           "rain_delay_threshold_mm", "heat_threshold_c")},
    }
    return forecast


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    farm_id: str | None = None


def _parse_answer(answer: str) -> dict:
    """Split the agent's URGENCY / ADVICE / ஆலோசனை / disclaimer answer into fields for display."""
    def field(label):
        m = re.search(rf"^{label}:\s*(.*?)(?=^\S+:|^Estimate only|\Z)", answer, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else None
    urgency = field("URGENCY")
    return {
        "urgency": urgency.split()[0].strip(",.") if urgency else None,
        "advice_en": field("ADVICE"),
        "advice_ta": field("ஆலோசனை"),
        "disclaimer": "Estimate only. Confirm with a local agriculture officer." if "Estimate only" in answer else None,
    }


@app.post("/api/chat")
def api_chat(body: ChatRequest):
    """One question in, the agent's answer and full Thought/Action/Observation trace out.
    With a farm_id, the agent reads that farm's sensor data and uses its settings by default."""
    if not body.farm_id:
        answer, trace = run_agent(body.message)
    else:
        farm = _farm_or_404(body.farm_id)
        if not farm["has_telemetry"]:
            raise HTTPException(400, f"{farm['name']} has no sensor data yet. Upload a CSV on the Farms page.")
        token = FARM.set(_farm_context(farm))
        try:
            answer, trace = run_agent(body.message, role=farm_role(farm))
        finally:
            FARM.reset(token)
    return {"answer": answer, "parsed": _parse_answer(answer), "trace": trace}


@app.get("/api/geocode")
def api_geocode(q: str = Query(..., min_length=2, max_length=100), count: int = Query(8, ge=1, le=20)):
    """Search any village, town or city by name (Open-Meteo geocoding, no key needed)."""
    try:
        resp = requests.get(GEOCODE_URL, params={"name": q, "count": count, "language": "en", "format": "json"},
                            timeout=6)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(503, f"place search unavailable: {e}") from e
    return [{"name": ", ".join(x for x in (r.get("name"), r.get("admin2"), r.get("admin1"), r.get("country")) if x),
             "lat": r["latitude"], "lon": r["longitude"]}
            for r in resp.json().get("results", [])]


@app.get("/api/farms")
def api_farms():
    return farm_store.list_farms()


@app.post("/api/farms", status_code=201)
def api_create_farm(body: FarmIn):
    return farm_store.create_farm(_validated(body))


@app.get("/api/farms/{farm_id}")
def api_get_farm(farm_id: str):
    return _farm_or_404(farm_id)


@app.put("/api/farms/{farm_id}")
def api_update_farm(farm_id: str, body: FarmIn):
    _farm_or_404(farm_id)
    return farm_store.update_farm(farm_id, _validated(body))


@app.delete("/api/farms/{farm_id}", status_code=204)
def api_delete_farm(farm_id: str):
    _farm_or_404(farm_id)
    farm_store.delete_farm(farm_id)
    return Response(status_code=204)


@app.get("/api/farms/{farm_id}/telemetry")
def api_farm_telemetry(farm_id: str):
    _farm_or_404(farm_id)
    df = farm_store.load_telemetry(farm_id)
    return {"rows": [] if df is None else _rows(df)}


@app.post("/api/farms/{farm_id}/telemetry")
def api_upload_farm_telemetry(farm_id: str, csv: UploadFile = File(...)):
    _farm_or_404(farm_id)
    try:
        df = farm_store.save_telemetry(farm_id, csv.file.read())
    except farm_store.FarmError as e:
        raise HTTPException(400, str(e)) from e
    return {"rows": len(df), "farm": farm_store.get_farm(farm_id)}


@app.post("/api/farms/{farm_id}/advice")
def api_farm_advice(farm_id: str):
    """Advisory for a farm using its own sensor data, crop, stage, area, soil and location."""
    farm = _farm_or_404(farm_id)
    df = farm_store.load_telemetry(farm_id)
    if df is None:
        raise HTTPException(400, f"{farm['name']} has no sensor data yet. Upload a CSV on the Farms page.")
    try:
        result = run_advisory(df, area_acres=farm["area_acres"], irrigation=farm["irrigation"],
                              days_after_transplanting=30, lat=farm["location"]["lat"],
                              lon=farm["location"]["lon"], crop=farm["crop"], stage=farm.get("stage"),
                              soil=farm["soil"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"input_source": "farm", "farm": farm, **result}


@app.get("/api/crops")
def api_crops():
    """Crops with dose models. Crops without stages use one whole-season target."""
    cfg = load_agronomy()
    return {name: {"stages": crop_stages(name, cfg), "flooded": bool(c.get("flooded")), "fao56_p": c.get("p")}
            for name, c in cfg["crops"].items()}


@app.get("/api/crop-fit")
def api_crop_fit(N: float | None = None, P: float | None = None, K: float | None = None,
                 temperature: float | None = None, humidity: float | None = None, ph: float | None = None,
                 crop: str | None = None):
    """Rank the Kaggle dataset's 22 crops by how well these readings fit their typical ranges."""
    result = crop_fit({"N": N, "P": P, "K": K, "temperature": temperature, "humidity": humidity, "ph": ph},
                      crop=crop)
    if not result["available"]:
        raise HTTPException(400, result["reason"])
    return result


@app.post("/api/advice")
def api_advice(
    csv: UploadFile | None = File(None),
    moisture: float | None = Form(None),
    n: float | None = Form(None),
    p: float | None = Form(None),
    k: float | None = Form(None),
    area_acres: float | None = Form(None),
    irrigation: str | None = Form(None),
    days_after_transplanting: int | None = Form(None),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    crop: str | None = Form(None),
    stage: str | None = Form(None),
    soil: str | None = Form(None),
    farm_id: str | None = Form(None),
):
    """Advisory from telemetry. Data source, in order: uploaded CSV, manual readings
    (moisture required, n/p/k optional), the farm's sensor file (farm_id), else the bundled
    sample CSV. With a farm_id, its location is the default for the weather."""
    d = _defaults()
    farm = _farm_or_404(farm_id) if farm_id else None
    if farm:
        d = {**d, "lat": farm["location"]["lat"], "lon": farm["location"]["lon"]}
    irrigation = (irrigation or d["irrigation"]).lower()
    if irrigation not in IRRIGATION_METHODS:
        raise HTTPException(400, f"irrigation must be one of {list(IRRIGATION_METHODS)}")

    if csv is not None and csv.filename:
        df, source = _read_csv(csv.file.read()), "upload"
    elif moisture is not None:
        row = {"moisture": moisture, "N": n, "P": p, "K": k}
        df, source = pd.DataFrame([{c: v for c, v in row.items() if v is not None}]), "manual"
    elif farm:
        df = farm_store.load_telemetry(farm["id"])
        if df is None:
            raise HTTPException(400, f"{farm['name']} has no sensor data yet. Upload a CSV on the Farms page.")
        source = "farm"
    else:
        df, source = pd.read_csv(SAMPLE_CSV_PATH), "sample"

    try:
        result = run_advisory(
            df,
            area_acres=d["area_acres"] if area_acres is None else area_acres,
            irrigation=irrigation,
            days_after_transplanting=(d["days_after_transplanting"] if days_after_transplanting is None
                                      else days_after_transplanting),
            lat=d["lat"] if lat is None else lat,
            lon=d["lon"] if lon is None else lon,
            crop=crop,
            stage=stage or None,
            soil=soil or d["soil"],
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {"input_source": source, **result}


@app.get("/api/voice")
def api_voice(text: str = Query(..., min_length=1, max_length=MAX_VOICE_CHARS),
              lang: str = Query("en", pattern="^(en|ta)$")):
    """Speak the advisory text. gTTS calls Google's TTS service, so it needs internet."""
    if gTTS is None:
        raise HTTPException(503, "text-to-speech unavailable: install gTTS")
    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except Exception as e:  # gTTS raises several network/HTTP error types
        raise HTTPException(503, f"text-to-speech failed: {e}") from e
    return Response(buf.getvalue(), media_type="audio/mpeg")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
