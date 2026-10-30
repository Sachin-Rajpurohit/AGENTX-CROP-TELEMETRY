# Uzhavan (உழவன்) — Crop Stress Telemetry & Advisory

**Soil sensor readings in, an actionable farm advisory out.**
Built for the AgentX Challenge, *Precision Agriculture* track, for farmers in Tamil Nadu: 23 crops (tomato plus the 22 crops of the Kaggle dataset).

| The brief asks for | How Uzhavan does it |
|---|---|
| Analyze 7 days of soil trends | Daily trend of moisture and N/P/K, drying rate, and days until the crop's irrigation trigger |
| Check rainfall risk with a weather tool | Live 48-hour rain and heat from Open-Meteo, with a 1-hour cache and an offline fallback that lowers confidence |
| Compute exact fertilizer / water dosage | Litres of water for the field today, and urea, DAP and MOP in kg for the field's area |
| Advice in simple regional language or English | Every answer in **Tamil and English**, with an URGENCY level and voice playback |

Input: each farm's own sensor CSV, readings typed in, or the sample `data/soil_telemetry.csv` (8 daily readings from a tomato field).

---

## Quick start

Requires Python 3.10+ and Node.js 18+.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # macOS/Linux: .venv/bin/pip
npm install
```

`requirements.txt` lists every Python package needed to run the agent, the API and the tests (checked with a fresh install); `npm install` installs the web app's packages.

Create a `.env` file with your Gemini key (used only by the chat agent):

```
GEMINI_API_KEY=your-key
```

Run the backend and the web app in two terminals:

```bash
.venv\Scripts\python server.py     # API on http://127.0.0.1:8000  (try it at /docs)
npm run dev                        # web app on http://localhost:3000
```

### The judges' command line

```bash
python main.py "My 1 acre tomato field is flowering. Should I irrigate today?"   # shows Thought / Action / Observation
python main.py --json "Should I irrigate my tomato field today?"                 # ONE JSON line: {"answer", "trace"}
python main.py --dry-run "anything"                                              # check the setup without an API key
```

Example answer (sample data, dry forecast):

```
URGENCY: RED
ADVICE: Soil is dry. Irrigate first, then apply fertilizer once the soil is moist. Crop: Tomato, flowering stage.
Soil moisture 22% (irrigate below 25.2%). Water: 35,972 litres today for 1 acre by drip, in 2 sessions.
Fertilizer for 1 acre: Urea 40.7 kg, DAP 120.9 kg, MOP 34.7 kg. Confidence: HIGH (100%).
ஆலோசனை: மண் வறண்டுள்ளது. முதலில் நீர் பாய்ச்சி, மண் ஈரமான பிறகு உரமிடவும். ...
Estimate only. Confirm with a local agriculture officer.
```

---

## How it works

Full backend guide (every calculation, the agent, the API and a testing checklist): [docs/BACKEND.md](docs/BACKEND.md).

The LLM does not do the agronomy. A deterministic, tested pipeline computes every number, and the agent and the web app both call it, so they always agree.

```
                 ┌── python main.py ── ReAct agent (Gemini) ── tools ──┐
farmer question ─┤                                                     ├─► agent/advisor.py pipeline
                 └── web app ── FastAPI (server.py) ───────────────────┘
                                                                          quality checks  (flatline, gaps, spikes, ranges)
                                                                        → 7-day trends
                                                                        → weather risk     (Open-Meteo, cached, fallback)
                                                                        → fertilizer + water doses
                                                                        → cross-signal rules
                                                                        → confidence score with reasons
                                                                        → English + Tamil advice, URGENCY
```

**ReAct agent** (`agent/core.py`): Thought → Action → Observation loop with a hard cap of 6 steps and a repeat guard (the same tool and arguments more than twice forces a final answer). Tools: `get_soil_readings`, `analyze_trend`, `get_weather_forecast`, `calculate_dosage`, `check_crop_suitability`, `get_crop_requirements`, `list_files`, `read_file`, `sql_query`, `calculator`. When `calculate_dosage` runs, the final answer is the pipeline's text word for word, so the LLM cannot change a dose or mistype the Tamil. If Gemini is unavailable, a scripted fallback calls the same real tools and answers only from their output.

**Rules** (`core/rules.py`), highest priority first:

| Rule | When | Decision |
|---|---|---|
| R5 | Moisture sensor flatlined or out of range | Inspect sensor, **no doses**, confidence capped at 0.40 |
| R6 | Moisture at or above field capacity (not paddy) | Drainage warning |
| R1 | Irrigation needed and ≥ 8 mm rain at ≥ 60% chance in 48 h | Wait for rain |
| R2 | Fertilizer due and ≥ 25 mm rain in 48 h | Delay fertilizer |
| R3 | Fertilizer due and soil below the trigger | Irrigate first, then fertilize |
| R9 / R10 | Soil below the trigger / nutrients below target | Irrigate / Fertilize |
| R4 | Max temperature ≥ 35°C while irrigating | Irrigate before 07:00 |

URGENCY: **RED** = act today, **YELLOW** = within 2–3 days, **GREEN** = no action needed.

**Confidence** starts at 100% and drops for a flatline (−35%), missing N/P/K (−20%), a fallback forecast (−15%), fewer than 5 days of data (−15%), a data gap (−10%) or a spike (−5%). The reasons are shown to the farmer.

---

## Where every number comes from

All constants live in `config/agronomy.yaml`. Each one names its source or is tagged `ASSUMPTION - verify vs TNAU/ICAR`.

**Irrigation trigger (FAO-56).** Telemetry moisture is volumetric water content. Irrigate when the crop has used a fraction *p* of the water the soil holds between field capacity (FC) and wilting point (PWP):

> trigger = FC − p × (FC − PWP)   (FAO-56, Allen et al. 1998, eq. 82–83)

| Crop | p (FAO-56 Table 22) | Trigger on clay loam (FC 32%, PWP 15%) | Fertilizer targets (kg/ha) |
|---|---|---|---|
| Tomato | 0.40 | 25.2% | by stage: seedling, vegetative, flowering, fruiting |
| Maize | 0.55 | 22.65% | whole season N120 P60 K50 |
| Cotton | 0.65 | 20.95% | whole season N80 P40 K40 |
| Rice (paddy) | kept ponded | re-flood below field capacity | by stage: seedling, tillering, flowering, ripening |

- **Soils** (selectable): clay loam (default) and sandy loam from Saxton & Rawls (2006); red soil derived from Tamil Nadu red-soil data (Malavath & Mani 2018), marked as an assumption.
- **Water dose:** refill the root zone (300 mm) to field capacity, at most 8 mm a day, split into sessions of 5 mm (drip) or 25 mm (flood), divided by efficiency (drip 0.90, flood 0.60). Likely rain (≥ 60% chance) counts toward the deficit.
- **Rice:** TNAU guidance — once the ponded water has gone, irrigate to 5 cm depth in one flooding.
- **Fertilizer:** nutrient gap ÷ use efficiency (N 0.60, P 0.50, K 0.70) → oxide (P × 2.29, K × 1.20) → product (urea 46% N, DAP 46% P₂O₅ + 18% N, MOP 60% K₂O). Urea is reduced by the nitrogen DAP already supplies. Targets come from `data/crop_requirements.json` (TNAU Agritech Portal & ICAR).
- **Why not the 50% trigger in the Mendeley data?** That dataset's `moisturePercentage` is a normalized reading from its own capacitive sensor, not volumetric water content, so it does not apply to `soil_telemetry.csv`.

### Datasets

| File | Source | Used for |
|---|---|---|
| `soil_telemetry.csv` | Challenge input | The farm's sensor readings |
| `Crop_recommendation.csv` | [Kaggle Crop Recommendation](https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset) (22 crops) | Crop suitability: which crops' typical N, P, K, pH, temperature and humidity ranges (10th–90th percentile) this field falls inside (rainfall excluded: the dataset uses seasonal totals). Also the N/P/K target (median) for the 19 crops without a TNAU figure. |
| `tomato_water_sensor_data.json`, `tomato irrigation dataset.csv` | [Mendeley: Dataset on irrigation for Tomato](https://data.mendeley.com/datasets/33cngpcrmx) (Kasera & Acharjee, CC BY 4.0) | Background on tomato thresholds; see the note above |
| `crop_requirements.json` | TNAU Agritech Portal & ICAR | N/P/K targets by crop and stage |

---

## Web app

White, soil-brown and leaf-green, with large text and Tamil beside every heading. On phones, navigation moves to a bottom tab bar. A farm switcher in the header chooses which field every page is about.

| Page | What it shows |
|---|---|
| **My Farm** | For the selected farm: today's advice as a big urgency banner, Tamil and English advice with 🔊 listen buttons, latest sensor readings, and a 7-day moisture chart with the "water below" line |
| **Ask Uzhavan** | Chat with a bilingual welcome message. Runs the same agent as `python main.py`; answers show the urgency, Tamil and English advice, and "How I worked this out" (the Thought / Action / Observation steps). History is kept across page switches and refreshes. |
| **Dose Calculator** | Crop, stage, acres, drip or flood, soil type, and sample data, typed readings or a CSV upload. Shows water in litres; urea, DAP and MOP in kg and 50 kg bags; moisture against the trigger; confidence; crop suitability; and how it was calculated. |
| **Weather** | 5-day rain and temperature for the selected farm or any place you search, what the forecast means for the field, and a live rain radar (Windy.com) |
| **Farms** | Farmers add their own fields: name, crop, sowing date (the growth stage is worked out from it), size in acres, cents or hectares, drip or flood, soil type, and location (search any village or town, or use this device's location). Upload each farm's sensor CSV (a template is provided) or use the sample data. |

## API

Interactive docs at `http://127.0.0.1:8000/docs` while `server.py` runs.

| Endpoint | Purpose |
|---|---|
| `POST /api/advice` | Full advisory. Form fields (all optional): `csv` file, or `moisture`, `n`, `p`, `k`, or `farm_id` (use that farm's sensor file and location); `crop`, `stage`, `days_after_transplanting`, `area_acres`, `irrigation` (drip/flood), `soil` (clay_loam / red_soil / sandy_loam), `lat`, `lon`. With no data it uses the sample file. |
| `POST /api/chat` | `{"message": "...", "farm_id": "..."}` → the agent's answer, parsed fields and trace. With a farm, the agent reads that farm's sensor file and uses its crop, size, soil, watering and location by default. |
| `GET/POST /api/farms`, `GET/PUT/DELETE /api/farms/{id}` | The farmer's fields. Stored in `.farmdata/` (set `AGENTX_FARM_DIR` to move it). No farm is created automatically. |
| `POST /api/farms/{id}/sample-data` | Give a farm the bundled sample sensor file |
| `GET/POST /api/farms/{id}/telemetry` | A farm's sensor readings; POST uploads a CSV (needs a `moisture` column) |
| `POST /api/farms/{id}/advice` | Advisory for a farm with its own data and settings |
| `GET /api/geocode?q=` | Search any place by name (Open-Meteo geocoding, no key) |
| `GET /api/weather?lat=&lon=` | 5-day forecast, 48 h risk and which rules it triggers |
| `GET /api/crops` | Supported crops, their stages and water rule |
| `GET /api/crop-fit?N=&P=&K=&temperature=&humidity=&ph=` | Crop suitability from the Kaggle dataset |
| `GET /api/sample` | Sample telemetry (CSV text and rows) and default settings |
| `GET /api/voice?text=&lang=en\|ta` | Spoken advice as MP3 (gTTS; needs internet) |
| `GET /api/health` | Liveness check |

---

## Tests

```bash
.venv\Scripts\python -m pytest -q
```

98 tests cover the dose arithmetic against hand-computed values, every rule, confidence scoring, each crop's thresholds, rice flooding, crop suitability, the API (with weather mocked), farms and place search, the agent loop and the judges' CLI contract.

## Project layout

```
main.py                 judges' entry point (ReAct agent, JSON contract)
server.py               FastAPI backend for the web app
farm_store.py           farms and their sensor files (.farmdata/)
agent/                  ReAct loop, Gemini client and fallback, prompt, advisory pipeline (advisor.py)
core/                   deterministic modules: quality, trends, weather, dosage, rules, confidence, crop_fit
config/agronomy.yaml    every agronomy constant, with its source
tools/                  agent tools (crop tools, data queries, calculator)
src/                    React + TypeScript + Tailwind web app
data/                   telemetry, crop requirements and the two challenge datasets
scripts/                small scripts that print dose intermediates and inspect the Mendeley data
tests/                  pytest suite
```

## Limitations

- **N/P/K units:** readings are compared directly with fertilizer requirements in kg/ha. The sample file does not state its units, so this is an assumption shown in every result.
- **Fertilizer targets:** tomato, rice, maize and cotton use TNAU/ICAR figures. The other 19 crops use the median N/P/K of their rows in the Kaggle dataset, which is not an agronomy recommendation; results say so and confidence drops by 10%. Crops outside the 23 get general advice only.
- **Rice:** "ponded water gone" is approximated as moisture below field capacity, because a soil sensor cannot see standing water.
- **Stage timings** (days after transplanting for each stage) and several efficiencies are assumptions, tagged in `config/agronomy.yaml`.
- **The Tamil text** is template-based and should be reviewed by a native speaker.
- **Internet:** the live forecast, voice and radar need it. Without it, the weather falls back to a cautious dry estimate and confidence drops.

*Estimate only. Confirm with a local agriculture officer.* · *இது மதிப்பீடு மட்டுமே. உள்ளூர் வேளாண் அலுவலரிடம் உறுதிப்படுத்தவும்.*
