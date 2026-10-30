# How the Uzhavan backend works

This is a guide to the backend for teammates and testers: what it uses, how a request flows through it, how every number is calculated, and how to test it.

---

## 1. The big picture

The backend has **two front doors** and **one brain**.

```
  python main.py "question"  ─┐                         ┌─ quality checks
  (judges' CLI, JSON contract) │                         ├─ 7-day trends
                               ├─► ReAct agent ─► tools ─┤
  POST /api/chat  ─────────────┘    (Gemini)             ├─ weather (Open-Meteo)
                                                         ├─ water + fertilizer doses
  POST /api/advice, /api/farms/{id}/advice ──────────────┤─ cross-signal rules
  (web app, direct calls)                                ├─ confidence score
                                                         ├─ crop suitability (Kaggle)
                                                         └─ English + Tamil advice, URGENCY
                                       agent/advisor.py  run_advisory()  ← the one brain
```

- **The pipeline** (`agent/advisor.py → run_advisory`) is deterministic: same input, same output, no AI involved. It computes every number.
- **The agent** (Gemini) decides *which tools to call with which arguments* for a free-text question. Its dose tool calls the same pipeline, and when the pipeline produces an answer, that answer is returned **word for word**. So the chat, the CLI and the web pages can never disagree on a number.

---

## 2. Technology used

| Purpose | Library / service | Where |
|---|---|---|
| Language | Python 3.10+ | everywhere |
| Web API | **FastAPI** + **Uvicorn** (server), **python-multipart** (file uploads), **Pydantic v2** (input validation) | `server.py` |
| Data handling | **pandas**, **numpy** | `core/`, `agent/advisor.py` |
| Config | **PyYAML** reading `config/agronomy.yaml` | `config/agronomy.py` |
| Weather | **Open-Meteo forecast API** (free, no key) via **requests**; 1-hour disk cache | `core/weather.py` |
| Place search | **Open-Meteo geocoding API** (free, no key) | `server.py /api/geocode` |
| LLM | **Google Gemini** via **google-genai** (`gemini-3.5-flash-lite`, 20 s timeout); **Groq** optional | `agent/llm.py` |
| Voice | **gTTS** (Google Text-to-Speech) for Tamil and English MP3 | `server.py /api/voice` |
| `.env` loading | **python-dotenv** | `main.py` |
| Storage | JSON file + one CSV per farm on disk (no database needed) | `farm_store.py` |
| Tests | **pytest**, FastAPI **TestClient** (**httpx**) | `tests/` |

Install everything with `pip install -r requirements.txt`.

---

## 3. Folder map

```
main.py              Judges' entry point. python main.py [--json] [--dry-run] "question"
server.py            FastAPI app: every /api endpoint, input validation, farm context for chat
farm_store.py        Farms: farms.json + <farm id>/soil_telemetry.csv in .farmdata/

agent/
  core.py            ReAct loop (Thought → Action → Observation), step cap, repeat guard
  llm.py             Gemini/Groq client, timeouts, the no-LLM fallback
  prompt_builder.py  System prompt (role, workflow, rules, answer format); farm context
  advisor.py         THE PIPELINE: run_advisory() + English/Tamil advice text

core/                Deterministic building blocks (each unit-tested)
  quality.py         Sensor checks: missing columns, out of range, flatline, spike, gap
  trends.py          7-day daily trends, drying rate, days until the irrigation trigger
  weather.py         Open-Meteo forecast → 48 h rain/heat risk; cache; offline fallback
  dosage_calc.py     Pure arithmetic: fertilizer products, irrigation litres
  dosage.py          Wraps dosage_calc with config values; rice flooding
  rules.py           Cross-signal rules → decision
  confidence.py      Confidence score with reasons
  crop_fit.py        Kaggle dataset: crop suitability and dataset N/P/K targets
  schema.py          Dataclasses shared by the modules

config/
  agronomy.yaml      EVERY agronomy constant, each with its source or an ASSUMPTION tag
  agronomy.py        Loader + helpers: crop names, thresholds, stages, targets
  __init__.py        Runtime settings: step cap, model names, data folder

tools/               What the agent can call
  crop_tools.py      get_soil_readings, analyze_trend, get_weather_forecast,
                     get_crop_requirements, calculate_dosage, check_crop_suitability
  data_query.py      list_files, read_file, sql_query
  calculator.py      safe arithmetic
  farm_context.py    The farm the current request is about

data/                Sample telemetry, crop requirements, Kaggle and Mendeley datasets
tests/               98 tests
```

---

## 4. What happens on one request

Example: `POST /api/advice` with a 2-acre tomato field at flowering.

1. **Validate input** (`server.py`): watering method, crop, stage, soil and area are checked. Bad values → HTTP 400 with a readable message.
2. **Pick the data:** an uploaded CSV, typed readings, a farm's own sensor file (`farm_id`), or the sample file.
3. **`run_advisory()`** runs these steps in order, recording each in a `trace`:

| Step | Module | What it produces |
|---|---|---|
| Quality | `core/quality.py` | List of issues and whether the moisture sensor has a fault |
| Trends | `core/trends.py` | Daily slope per column, falling/rising/stable, days until the trigger |
| Weather | `core/weather.py` | Rain in the next 48 h (mm, max %), max temperature in 3 days, source |
| Thresholds | `config/agronomy.py` | Field capacity, wilting point, irrigation trigger for this crop and soil |
| Fertilizer | `core/dosage.py` | Urea, DAP, MOP in kg/ha and kg for the area |
| Water | `core/dosage.py` | Litres today, sessions, days to refill |
| Rules | `core/rules.py` | The decision and every rule that fired |
| Confidence | `core/confidence.py` | Score, HIGH/MEDIUM/LOW, reasons |
| Crop fit | `core/crop_fit.py` | Best-matching crops from the Kaggle dataset |
| Advice | `agent/advisor.py` | English and Tamil text, URGENCY, the judges' answer string |

4. **Response:** one JSON object with all of the above (`decision`, `urgency`, `doses`, `confidence`, `advisory`, `answer`, `weather`, `quality`, `trends`, `crop_fit`, `assumptions`, `trace`).

---

## 5. How each number is calculated

All constants come from `config/agronomy.yaml`.

### 5.1 Sensor quality (`core/quality.py`)

| Check | Rule | Severity |
|---|---|---|
| Missing column | moisture, N, P, K, pH or temperature not found (case-insensitive, synonyms like `soil_moisture`, `nitrogen`) | WARN |
| Out of range | moisture outside 0–100, pH outside 3–10, temperature outside −5–60 °C | CRITICAL |
| Flatline | moisture, temperature or humidity identical for ≥ 3 readings in a row at the end | CRITICAL |
| Constant N/P/K | same N/P/K in every row (normal for slow-changing nutrients) | INFO only |
| Spike | with ≥ 6 readings: a value more than 4 × MAD from the median | WARN |
| Gap | a time gap more than 2 × the median interval between readings | WARN |

A CRITICAL flatline or out-of-range **on moisture** is a sensor fault: no doses are given, the decision is "inspect sensor", and confidence is capped at 40%. (Exception: a flooded paddy reading constantly at saturation is normal, not a fault.)

### 5.2 Trends (`core/trends.py`)
Readings are averaged per day and the last 7 days are kept. A straight-line fit gives the slope per day: below −0.05 is *falling*, above +0.05 *rising*, otherwise *stable*. For moisture it also finds wetting events (a day-to-day jump > 3 points) and, from the drying rate since the last wetting, the days until moisture reaches the trigger.

### 5.3 Weather (`core/weather.py`)
Open-Meteo daily forecast for the farm's coordinates: `rain_mm_48h` (today + tomorrow), `rain_prob_48h` (max of the two), `tmax_next3`. Responses are cached on disk for 1 hour (`.cache/weather`). If the API is unreachable the module **never crashes**: it returns a cautious dry forecast with `source: "fallback"`, which lowers confidence by 15%.

### 5.4 Irrigation trigger (FAO-56)
Telemetry moisture is volumetric water content (%). FAO-56 (Allen et al. 1998, eq. 82–83):

> **trigger = FC − p × (FC − PWP)**

- FC (field capacity) and PWP (wilting point) come from the soil type: clay loam 32/15 (default), red soil 26/10, sandy loam 14/5.
- p is the crop's depletion fraction from FAO-56 Table 22 (tomato 0.40, maize 0.55, cotton 0.65, banana 0.35, …). Crops FAO-56 does not list use the closest listed crop, tagged ASSUMPTION.

Worked example, tomato on clay loam: 32 − 0.40 × (32 − 15) = **25.2%**.

### 5.5 Water dose (`core/dosage_calc.py → irrigation_plan`)
If moisture < trigger, refill the 300 mm root zone to field capacity:

```
deficit_mm   = (FC − moisture) / 100 × 300 − effective rain
daily_mm     = min(deficit_mm, 8)                     # max 8 mm/day
litres/day   = daily_mm / efficiency × area_m²        # 1 mm on 1 m² = 1 litre; drip 0.90, flood 0.60
sessions     = ceil(daily_mm / 5)  (drip)  or  / 25 (flood)
days_to_refill = ceil(deficit_mm / 8)
```
Effective rain = 0.8 × forecast rain, counted only when the chance is ≥ 60%.

Worked example, sample data (moisture 22%), 1 acre, drip: deficit = (32 − 22)/100 × 300 = 30 mm → 8 mm today → 8 / 0.9 × 4046.86 m² = **35,972 litres** in 2 sessions, repeated for about 4 days.

**Rice** is kept flooded instead (TNAU): once moisture drops below field capacity (ponded water gone), flood to 5 cm in one go: 50 mm / 0.60 × area.

### 5.6 Fertilizer dose (`core/dosage_calc.py → plan_fertilizer`)
For each nutrient: gap = target − measured (kg/ha, never negative). Then:

```
nutrient to apply = gap / use efficiency            (N 0.60, P 0.50, K 0.70)
oxide             = nutrient × factor               (P → P₂O₅ × 2.29, K → K₂O × 1.20)
DAP  = P₂O₅ / 0.46        MOP = K₂O / 0.60
N already in DAP  = DAP × 0.18
Urea = (N to apply − N in DAP) / 0.46               (never negative)
kg for the farm   = kg/ha × acres × 0.404686
```

Worked example, tomato at flowering (target N100 P50 K60, measured N40 P20 K30), 1 acre:
N 60/0.6 = 100 kg N · P 30/0.5 = 60 kg P → 137.4 kg P₂O₅ → **DAP 298.7 kg/ha** · K 30/0.7 = 42.9 → 51.4 kg K₂O → **MOP 85.7 kg/ha** · N in DAP 53.8 → **urea 100.5 kg/ha** → per acre: **urea 40.7, DAP 120.9, MOP 34.7 kg**. These exact values are in the tests.

**Where targets come from:**
- Tomato and rice (per growth stage), maize and cotton: `data/crop_requirements.json` (TNAU Agritech Portal & ICAR).
- The other 19 crops: no TNAU figure is bundled, so the target is the **median N/P/K of that crop's 100 rows in the Kaggle dataset**, the typical level where it grows well. The response says so and confidence drops by 10%.

**Growth stage:** set by the farmer, or worked out from the sowing date (e.g. tomato: ≤ 20 days seedling, ≤ 45 vegetative, ≤ 70 flowering, then fruiting).

### 5.7 Rules (`core/rules.py`)
Every rule whose condition holds fires; the highest-priority one sets the decision.

| Priority | Rule | Condition | Decision |
|---|---|---|---|
| 1 | R5 | Moisture sensor fault | INSPECT_SENSOR (no doses) |
| 2 | R6 | Moisture ≥ field capacity (not paddy) | DRAINAGE_WARNING |
| 3 | R1 | Water needed and ≥ 8 mm rain at ≥ 60% in 48 h | WAIT_FOR_RAIN |
| 4 | R2 | Fertilizer due and ≥ 25 mm rain in 48 h | DELAY_FERTILIZER |
| 5 | R3 | Fertilizer due and soil below trigger | IRRIGATE_THEN_FERTILIZE |
| 6 | R9 | Soil below trigger | IRRIGATE |
| 7 | R10 | A nutrient below target | FERTILIZE |
| — | R4 | Max ≥ 35 °C while irrigating | adds "water before 7 am" |
| — | R8 | Nothing fired | NO_ACTION |

URGENCY: **RED** (act today) for sensor fault, drainage, irrigate; **YELLOW** (2–3 days) for wait-for-rain, delay or add fertilizer; **GREEN** for no action.

### 5.8 Confidence (`core/confidence.py`)
Starts at 100% and loses: flatline 35%, missing N/P/K 20%, weather fallback 15%, fewer than 5 days of data 15%, dataset-based target 10%, data gap 10%, spike 5%. HIGH ≥ 70%, MEDIUM ≥ 40%, else LOW. Capped at 40% on a sensor fault. Every deduction is listed in `confidence.reasons`.

### 5.9 Crop suitability (`core/crop_fit.py`)
For each of the 22 Kaggle crops, the 10th–90th percentile of N, P, K, temperature, humidity and pH. The field is ranked by how many of its readings fall inside each crop's range (ties broken by distance from the crop's average). Rainfall is excluded because the dataset uses seasonal totals.

---

## 6. The AI agent

### 6.1 The loop (`agent/core.py`)
Each turn the model replies with one JSON object: either `{"thought", "action", "args"}` to call a tool, or `{"thought", "final_answer"}`.

- **Step cap:** at most 6 steps (`MAX_ITERATIONS`), then it must answer.
- **Repeat guard:** the same tool with the same arguments more than twice forces a final answer.
- **No answering from memory:** an agricultural question answered without any tool call is sent back once ("call get_soil_readings first").
- **Tool errors become observations** (`ERROR: …`), never crashes.
- **Verbatim answer:** if `calculate_dosage` ran, its `answer_draft` is returned exactly, so the model cannot change a number or mistype the Tamil.
- **Output:** `answer` plus `trace` = list of `{thought, tool, args, observation}`.

### 6.2 Tools

| Tool | What it does |
|---|---|
| `get_soil_readings` | Mean and latest value of each sensor column |
| `analyze_trend` | Slope and falling/rising/stable for one column; for moisture also the crop's trigger |
| `get_weather_forecast` | 48 h rain and heat risk for the farm's location |
| `calculate_dosage` | Runs the full pipeline; returns decision, urgency, water, fertilizer, `answer_draft` |
| `get_crop_requirements` | N/P/K targets, stages, irrigation trigger and source for any of the 23 crops |
| `check_crop_suitability` | Which of the 22 dataset crops suit the soil |
| `list_files`, `read_file`, `sql_query` | Read the data files; simple SQL over a CSV |
| `calculator` | Safe arithmetic |

### 6.3 The model and the fallback (`agent/llm.py`)
Gemini `gemini-3.5-flash-lite` (set `GEMINI_MODEL` to change), 20-second timeout per call, retries on rate limits. If the model fails (no key, timeout, outage), the **fallback** runs the real tools in order (soil → trend → weather → dosage), taking crop, stage and acres from the question, and answers **only** from the dosage tool's output. Every fallback is logged to stderr.

### 6.4 Farm context
`POST /api/chat` with a `farm_id` sets the farm for that request (`tools/farm_context.py`). Tools then read **that farm's** sensor file and default to its crop, stage (or days since planting), area, soil, watering and location. The prompt names the farm. The CLI has no farm and uses `data/soil_telemetry.csv`.

---

## 7. Farms (`farm_store.py`)
- `.farmdata/farms.json` holds the list; each farm's sensor file is `.farmdata/<id>/soil_telemetry.csv`. Set `AGENTX_FARM_DIR` to store it elsewhere.
- A farm: name, crop, stage (optional), sowing date (optional), size in acres plus the unit the farmer used (acre/cent/hectare), watering method, soil type, location (name, lat, lon).
- Uploaded CSVs are checked before saving (≤ 2 MB, must parse, needs a numeric `moisture` column). Writes use a lock and an atomic file replace.
- No farm is created automatically. `POST /api/farms/{id}/sample-data` gives a farm the bundled sample file for trying the app.

---

## 8. API reference
Interactive docs: `http://127.0.0.1:8000/docs` while `python server.py` runs.

| Method & path | Input | Output |
|---|---|---|
| `GET /api/health` | — | `{"status": "ok"}` |
| `POST /api/advice` | form: `csv` file **or** `moisture`,`n`,`p`,`k` **or** `farm_id`; optional `crop`, `stage`, `days_after_transplanting`, `area_acres`, `irrigation`, `soil`, `lat`, `lon` | Full advisory |
| `POST /api/chat` | JSON `{"message", "farm_id"?}` | `answer`, `parsed` (urgency, advice_en, advice_ta, disclaimer), `trace` |
| `GET /api/crops` | — | 23 crops: English/Tamil names, stages, flooded, FAO-56 p, target source |
| `GET /api/crop-fit` | query `N,P,K,temperature,humidity,ph`, `crop` | Ranked crop matches |
| `GET /api/weather` | query `lat`, `lon` | 5 days + 48 h risk + which rules it triggers |
| `GET /api/geocode` | query `q` (≥ 2 chars) | Matching places with lat/lon |
| `GET /api/farms` · `POST /api/farms` | JSON farm | List / created farm |
| `GET`·`PUT`·`DELETE /api/farms/{id}` | JSON farm for PUT | Farm / 204 |
| `GET`·`POST /api/farms/{id}/telemetry` | multipart `csv` for POST | Rows / row count |
| `POST /api/farms/{id}/sample-data` | — | Row count |
| `POST /api/farms/{id}/advice` | — | Full advisory for that farm |
| `GET /api/sample` | — | Sample CSV text, rows and defaults |
| `GET /api/voice` | query `text` (≤ 1000), `lang` = `en` or `ta` | MP3 audio |

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/advice -F crop=banana -F moisture=22 -F n=40 -F p=20 -F k=30 -F area_acres=2
curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"message\": \"Should I irrigate my 2 acre paddy today?\"}"
```

**Error codes:** 400 = invalid value or unusable CSV (message says why) · 404 = unknown farm · 422 = wrong type or missing field · 503 = voice or place search unavailable (needs internet). The weather never fails a request; it falls back.

---

## 9. Testing it thoroughly

```bash
.venv\Scripts\python -m pytest -q          # 98 tests, offline (weather and LLM mocked)
.venv\Scripts\python main.py --json --dry-run "hi"     # contract check without an API key
```

What the tests cover: the dose arithmetic against hand-computed values; every rule; confidence; thresholds for each crop and soil; rice flooding; all 22 dataset crops; crop names; crop suitability; every API endpoint and its validation; farms (create, update, delete, upload, sample data, planting date → stage); the agent loop, step cap, tool errors, verbatim answers; farm context; the CLI contract.

**Things worth probing by hand** (and what should happen):

| Try | Expected |
|---|---|
| CSV with moisture stuck at one value | INSPECT_SENSOR, no doses, confidence ≤ 40% |
| CSV with no `moisture` column, or empty | 400 with a clear message |
| Moisture above field capacity (e.g. 40) | DRAINAGE_WARNING (except rice) |
| Readings typed in, one row | Works; confidence drops for < 5 days of data |
| No N/P/K | Water advice only; "missing NPK readings" |
| Crop `dragonfruit` | 400: lists the 23 supported crops |
| Crop `kidney beans`, `toor`, `paddy` | Recognised as kidneybeans, pigeonpeas, rice |
| `area_acres=2` vs `1` | Every dose doubles |
| `irrigation=flood` vs `drip` | 1.5 × the water |
| Turn off the internet | Weather `source: fallback`, confidence −15%; still answers |
| Remove `GEMINI_API_KEY` | Chat still answers through the fallback, from real tool output |
| Ask the chat "Hello" | Greeting, no tools |

---

## 10. Known limitations
- N/P/K units in the sample are not stated; readings are compared with targets as kg/ha (shown in every response).
- 19 crops use dataset-median targets, not agronomy recommendations (flagged, −10% confidence).
- The 300 mm root zone and 8 mm/day cap are general assumptions; tree crops root deeper.
- Rice "ponded water gone" is approximated as moisture below field capacity.
- Tamil text is template-based and should be reviewed by a native speaker.
