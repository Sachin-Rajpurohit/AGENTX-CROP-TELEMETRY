"""FastAPI backend for AGENTX Crop Telemetry Sensor-to-Dose Advisor.

Run:  python server.py   (or: uvicorn server:app --port 8000)

Endpoints:
  GET  /api/health                        liveness check
  GET  /api/sample                        bundled sample telemetry CSV + default parameters
  POST /api/advice                        multipart form, see api_advice() for fields
  GET  /api/voice?text=...&lang=en|ta     spoken advisory as audio/mpeg (needs gTTS + internet)
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from agent.advisor import run_advisory
from config import DATA_DIR
from config.agronomy import load_agronomy
from core.dosage import IRRIGATION_METHODS

SAMPLE_CSV_PATH = Path(DATA_DIR) / "soil_telemetry.csv"
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_VOICE_CHARS = 1000

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

app = FastAPI(title="AGENTX Crop Telemetry", description="Sensor-to-Dose Advisor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("AGENTX_CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
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
        "soil": cfg["default_soil"],
        "soil_types": list(cfg["soil_types"]),
    }


def _read_csv(data: bytes) -> pd.DataFrame:
    if len(data) > MAX_CSV_BYTES:
        raise HTTPException(413, f"CSV larger than {MAX_CSV_BYTES // (1024 * 1024)} MB")
    try:
        df = pd.read_csv(io.BytesIO(data))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise HTTPException(400, f"could not parse CSV: {e}") from e
    if df.empty:
        raise HTTPException(400, "CSV has no rows")
    return df


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/sample")
def api_sample():
    """Bundled sample telemetry and the default form parameters."""
    return {"csv": SAMPLE_CSV_PATH.read_text(encoding="utf-8"), "metadata": _defaults()}


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
    soil: str | None = Form(None),
):
    """Advisory from telemetry. Data source, in order: uploaded CSV, manual readings
    (moisture required, n/p/k optional), else the bundled sample CSV."""
    d = _defaults()
    irrigation = (irrigation or d["irrigation"]).lower()
    if irrigation not in IRRIGATION_METHODS:
        raise HTTPException(400, f"irrigation must be one of {list(IRRIGATION_METHODS)}")

    if csv is not None and csv.filename:
        df, source = _read_csv(csv.file.read()), "upload"
    elif moisture is not None:
        row = {"moisture": moisture, "N": n, "P": p, "K": k}
        df, source = pd.DataFrame([{c: v for c, v in row.items() if v is not None}]), "manual"
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
