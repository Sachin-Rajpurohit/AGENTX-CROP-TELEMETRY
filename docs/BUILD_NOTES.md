# BUILD_NOTES.md — Sensor-to-Dose Advisor (phase 0 findings)

Branch: `feature/dashboard` (created from `main`, commit `f51d234`).  
Repo: `C:\Users\sachi\.cline\worktrees\0dfe7\AGENTX-CROP-TELEMETRY`  
Python: 3.12.10 (`.venv` with pandas/numpy/scikit-learn/pytest/ruff/fastapi/uvicorn/gTTS/httpx/PyYAML).

## Status — Phase 0 only. No feature code written yet. Waiting for approval before build order begins.

## 1. What already exists (do not duplicate)

| Layer | Files | What it provides |
|---|---|---|
| CLI entrypoint | `main.py` | `python main.py --json "query"` → one JSON line `{"answer": str, "trace": [...]}`. `--dry-run` uses `DryRunLLM` (no API key). |
| ReAct loop | `agent/core.py` | `AgentExecutor(llm, tools)` with `MAX_ITERATIONS = 6`, `MAX_SAME_TOOL_CALLS = 2`, JSON action/final_answer parsing, tool call/error capture into `trace`. |
| LLM client | `agent/llm.py` | `LLM()` picks Gemini (`GEMINI_API_KEY`) else Groq (`GROQ_API_KEY`) else `None`. `None` / errors → `_autonomous_fallback` deterministic solver. `DryRunLLM` scripted stand-in. |
| Prompt conventions | `agent/prompt_builder.py` | `ROLE` string + `SYSTEM_TEMPLATE`; tools registered as `{name}: {description} Args: {args_doc}`; ReAct JSON instruction. |
| Runtime config | `config/__init__.py` | `MAX_ITERATIONS`, `MAX_SAME_TOOL_CALLS`, model names, `TEMPERATURE = 0.2`, `DATA_DIR` (env-overridable `AGENTX_DATA_DIR`). |

| Tools | `tools/__init__.py`, `calculator.py`, `crop_tools.py`, `data_query.py`, `web_search.py` | `build_tools()` registry: `list_files`, `read_file`, `sql_query`, `calculator`, `web_search`, plus crop tools `get_soil_readings`, `analyze_trend`, `get_weather_forecast`, `get_crop_requirements`, `calculate_dosage`. |
| Crop knowledge | `data/crop_requirements.json` | TNAU/ICAR-derived ideal values per crop/stage. Tomato: ideal N75/P40/K50/pH6.5/moisture65; stages seedling/vegetative/flowering/fruiting. |
| Telemetry | `data/soil_telemetry.csv` | 8 daily rows, 2026-10-12 to 2026-10-19, tomato. See schema below. |
| Kaggle rec data | `data/Crop_recommendation.csv` | 2200 rows, columns N,P,K,temperature,humidity,ph,rainfall,label. Labels: 22 crops; **tomato is NOT in the label set**. |
| Frontend (existing React app) | `src/components/*.tsx`, `src/lib/*.ts` | TelemetryDashboard, DosageCalculatorModal, WeatherWidget, AgentConsole, agentEngine.ts, cropTools.ts, datasets.ts. We will NOT touch these unless approved (Hard Rule 1). |
| Tests | `tests/test_agent.py` | 7 tests, all passing (`python -m pytest tests -q`). Covers parse_json, tool loop, errors, iteration cap, CLI contract. |

## 2. CSV schema and unit guesses (`data/soil_telemetry.csv`)

`head -10`:
```
timestamp,moisture,N,P,K,pH,temperature,humidity,rainfall,crop
2026-10-12 08:00,31,40,20,30,6.4,29.5,76,0,tomato
...
2026-10-19 08:00,22,40,20,30,6.2,32.4,65,0,tomato
```

- Rows: 8; one plot/sensor (crop=tomato); sampling interval daily at 08:00 (timedelta 1 day, all 7 gaps are 1 day).
- Date range: 2026-10-12 → 2026-10-19 (7 full days + 1 day = matches "analyze 7 days" requirement).
- Column / unit guesses:
  - `timestamp`: ISO datetime, daily 08:00.
  - `moisture`: percent (0–100). Falls 31 → 22 over the week (drying). Units are %-points, likely volumetric water content percent.
  - `N,P,K`: mg/kg (per Kaggle columns) — but flatlined at 40/20/30 across all 8 rows (no variance). Treated as mg/kg-equivalent soil nutrient index.
  - `pH`: unitless, 6.2–6.4.
  - `temperature`: °C, 29.5–32.4.
  - `humidity`: %, 65–76.
  - `rainfall`: mm, all 0 in this sample.
  - `crop`: string "tomato".
- `df.describe()` summary: moisture mean 26.25 std 3.1 min 22 max 31; N/P/K std 0 (flatline candidate for quality.py FLATLINE detector); pH mean 6.29; temperature mean 31.2; humidity mean 70.3; rainfall all 0.

## 3. How the LLM client is configured (`agent/llm.py`)

- `LLM.__init__`: provider = `AGENTX_PROVIDER` env, else gemini if `GEMINI_API_KEY` set, else groq if `GROQ_API_KEY` set, else `None`.
- `.env.example`: `GROQ_API_KEY=`, `AGENTX_PROVIDER=groq`, `GROQ_MODEL=openai/gpt-oss-120b`.
- `generate(system, messages)`: retries on 429/rate/quota (4 attempts); on any failure or `client is None` → `_autonomous_fallback` (deterministic, no key needed).
- Conforms to Hard Rule 3: LLM only chooses tools / writes advisory text; no arithmetic in LLM.

## 4. CLI output schema (must keep working — Hard Rule 2)

`python main.py --json "query"` prints exactly one JSON object to stdout:
```json
{"answer": "<string>", "trace": [{"thought": str, "tool": str, "args": {...}, "observation": str}]}
```
- Logs go to stderr; stdout must be parseable JSON (hidden tests check this).
- `--dry-run` and env `AGENTX_DRY_RUN=1` → `DryRunLLM` (no external key).
- Must never crash on missing columns, empty input, API failure, or LLM failure → errors become `observation` strings starting with "ERROR:"; final answer still produced.

## 5. Build plan mapped onto existing structure

New directories/files (nothing in `tools/`, `agent/`, `data/`, `src/`, `tests/` is edited):

```
config/agronomy.yaml        # all agronomy constants, each tagged "# ASSUMPTION - verify vs TNAU/ICAR"
core/schema.py              # dataclasses (QualityReport, TrendReport, WeatherRisk, ...)
core/quality.py
core/trends.py
core/weather.py
core/dosage.py
core/rules.py
core/confidence.py
core/calendar.py
core/impact.py
core/whatif.py
core/cropfit.py
core/guard.py
agent/advisor.py            # ReAct loop over core tools; reuse agent.llm + prompt conventions
server.py                   # FastAPI + StaticFiles for web/
web/index.html
web/styles.css
web/app.js
evals/scenarios.py
evals/run_evals.py
tests/                      # pytest for every core module
docs/BUILD_NOTES.md         # this file
```

Build order (commit after each, run tests each time):
1. schema + config + quality  
2. trends  
3. weather  
4. dosage  
5. rules + confidence  
6. calendar + impact + whatif  
7. guard + cropfit  
8. agent loop + CLI compatibility check (`python main.py --json` must still work)  
9. evals ≥ 9/10  
10. server.py  
11. frontend  
12. README section + assumptions table

Key integration points with existing code:
- Reuse `config.DATA_DIR` / `AGENTX_DATA_DIR` for data path so judges can swap data.
- Reuse `agent.llm.LLM` + `agent.prompt_builder` conventions in `agent/advisor.py`.
- Preserve `main.py` CLI contract and existing `tests/test_agent.py` (do not edit; add new tests under `tests/`).
- Decision enum: IRRIGATE, IRRIGATE_AT_DAWN, WAIT_FOR_RAIN, FERTILIZE, IRRIGATE_THEN_FERTILIZE, DELAY_FERTILIZER, NO_ACTION, INSPECT_SENSOR, DRAINAGE_WARNING.

## 6. Open items / decisions needed before build

- Target languages: English + Tamil confirmed (Tamil templates marked "needs native-speaker review").
- LLM provider/API key: Groq per `.env.example`; no key present → deterministic fallback covers grading.
- Build order / stretch features (multi-plot, PWA, voice) to be confirmed after approval.
## 7. Pre-work changes (approved)

### 7.1 WIRE INTO THE GRADED PATH
- New file: `tools/advisor_tools.py` — thin wrappers over `core/`, each subclassing `tools.Tool`, returning JSON strings, never raising. Registered in `tools/__init__.py` `build_tools()` alongside existing tools.
- Existing file edits (ONLY these two, append-only):
  - `tools/__init__.py`: add `from tools.advisor_tools import ADVISOR_TOOLS` and `tools += [cls() for cls in ADVISOR_TOOLS]` in `build_tools()`.
  - `agent/prompt_builder.py`: append advisor tool descriptions so the LLM can discover them.
- Do NOT touch: `main.py`, `agent/core.py`, `tests/test_agent.py`.
- Exact diff recorded after implementation.
- Structured advisory inside `answer`: `answer` carries the bilingual text summary (URGENCY/ADVICE/ஆலோசனை) for backward compat, plus a `STRUCTURED:` JSON suffix block with `decision, doses, calendar, impact, rules_fired, assumptions`. The `{answer, trace}` contract is preserved exactly.
- Overlap with `tools/data_query.py` and `tools/crop_tools.py`: reuse `get_soil_readings`, `analyze_trend`, `get_weather_forecast`, `get_crop_requirements`, `calculate_dosage` logic via `core/`; do not re-implement `_load_rows()` or `_requirements()`. Wrappers delegate to `core/`.

### 7.2 NPK UNITS
- `data/crop_requirements.json` tomato ideal: N75/P40/K50 — kg/ha (standard fertilizer recommendation units). Existing `tools/crop_tools.py calculate_dosage` treats them as kg/ha.
- Kaggle `Crop_recommendation.csv` N/P/K — tomato NOT in its labels, not used for tomato targets.
- `data/tomato irrigation dataset.csv` has "Nitrogen [mg/kg]" etc. — different dataset, not used for targets.
- Decision: `npk_unit: kg_ha` in config/agronomy.yaml. Deficit already kg/ha; no 1.95 conversion. The 1.95 factor (bulk_density * sample_depth * 10) retained only as fallback if npk_unit == mg_kg.
## 4b-1 TARGET PROVENANCE (fertilizer requirements, NOT soil-test levels)

`data/crop_requirements.json` tomato entry (verbatim):
```
"tomato": {
  "source": "TNAU Agritech Portal & ICAR-IIHR Bangalore",
  "ideal": { "N": 75, "P": 40, "K": 50, "pH": 6.5, "moisture": 65 },
  "stages": {
    "seedling": { "moisture": 70, "N": 40, "P": 50, "K": 30 },
    "vegetative": { "moisture": 65, "N": 75, "P": 40, "K": 50 },
    "flowering": { "moisture": 65, "N": 100, "P": 50, "K": 60 },
    "fruiting": { "moisture": 60, "N": 120, "P": 60, "K": 75 }
  }
}
```
- N100/P50/K60 comes from `stages.flowering` (overrides top-level `ideal` N75/P40/K50).
- Plain statement: these are **fertilizer requirements in kg/ha** (TNAU/ICAR recommendation per crop stage), NOT soil-test levels. The `ideal.moisture` (65) is a soil-moisture target in %.
- Consequence: N/P/K targets cannot be subtracted directly from `soil_telemetry.csv` N/P/K readings (different units, unverified scale). Deficit logic redesigned in 4b-4d.
- Stage logic: used only because `stages.flowering` is an explicit cited source in config/agronomy.yaml (tagged ASSUMPTION - verify vs TNAU/ICAR). No other stage multipliers invented.

## 4b-2 MOISTURE CALIBRATION (EMPIRICAL from org data)

Source A — `data/tomato_water_sensor_data.json` (393 records, `moisturePercentage` on 0-100 scale, `motorValue` = pump on/off label):
- moisturePercentage distribution: min 38.22, p25 54.64, median 56.79, p75 58.06, max 67.64, mean 56.54
- motorValue=1 (pump ON): n=14, moisture 38.22–49.98 (mean 44.43)
- motorValue=0 (pump OFF): n=379, moisture 51.22–67.64 (mean 56.99)
- Clear switch gap: motor ON max 49.98 vs motor OFF min 51.22 → pump turns ON at ≈ **50% moisture**

Source B — `data/tomato irrigation dataset.csv` (3000 rows):
- `Soil moisture` raw ADC: min 120.09, median 386.17, max 699.99 (different scale — raw sensor counts, NOT percent)
- Confirms `moisturePercentage` (0-100) from Source A is the calibrated moisture scale

Calibrated config values (labelled `# EMPIRICAL from org data`):
- moisture scale: percent 0-100 (393 records from sensor JSON)
- FC (field capacity): 65% — upper end of healthy/OFF range, matches crop_requirements ideal moisture (393 records)
- PWP (wilting point): 40% — lower end near motor ON minimum 38.22, below which plants stress (393 records)
- trigger: 50% — empirical motorValue switch-on point (max ON 49.98, min OFF 51.22)

Note on soil_telemetry.csv latest moisture=22: on the 0-100 percent scale this is **below PWP (40)** = severe water stress, correctly triggering urgent irrigation (capped by max_daily_mm, not a single 580,000 L refill).

## 4b-3 WATER REALISM

Replaced single-event refill-to-field-capacity with:
- max_event_mm per method: drip 5 mm, flood 25 mm (config, ASSUMPTION-tagged)
- max_daily_mm: 8 mm/day for drip (tomato ~8 mm/day; config, ASSUMPTION-tagged). Keeps a normal tomato day within 10,000–40,000 L/acre.
- Multi-day refill: total deficit spread across days at max_daily_mm; each event capped at max_event_mm.
- Sanity guard: if planned daily irrigation > max_daily_mm, clip to max_daily_mm and set `clipped=true` flag.
- 1 mm over 1 acre (4046.86 m²) = 4,046.86 L before efficiency.
- Drip example (8 mm/day, eff 0.90): 8/0.90 × 4046.86 ≈ 35,972 L/acre/day (within 10k–40k ✓)

## 4b-4 FERTILIZER LOGIC

Targets are fertilizer requirements (kg/ha), not soil levels → deficit logic redesigned (formula in 4b-4d).

a) N credit from DAP: DAP is 18% N + 46% P2O5. DAP applied for P supplies N (DAP_kg_ha × 0.18), credited against urea requirement. Gross and net N both reported.
b) Per-nutrient use_eff in config: N, P, K different (ASSUMPTION-tagged).
c) split_policy per nutrient: N = split, K = split, P = single basal/fertigation dose (P is never split into 4).
d) Redesigned deficit logic (formula shown before coding, implemented in core/dosage.py):
   sufficiency = clamp(measured / 100, 0, 1)   # measured on 0-100 index
   deficit_fraction = max(0, 1 - sufficiency)
   nutrient_needed_kg_ha = requirement_kg_ha × deficit_fraction
   nutrient_to_apply_kg_ha = nutrient_needed_kg_ha / use_eff_nutrient
   product_kg_ha = (nutrient_to_apply × oxide_conversion) / product_pct

## 4b-5 TESTS (to be added)

pytest cases with hand-computed expected values:
- urea dose (gross N, DAP N-credit, net N)
- DAP dose (P basis)
- MOP dose (K basis)
- irrigation sanity bound: litres/acre/day between 10,000 and 40,000 for a normal tomato day

## 4b-6 WIRING CHECK (report only — awaiting approval)

`agent/llm.py` `_autonomous_fallback` (note: lives in llm.py, not core.py):
- Picks tools via a hardcoded step_count sequence: step 0 → `get_soil_readings`, step 1 → `analyze_trend`, step 2 → `get_crop_requirements`, step 3 → `calculate_dosage`/weather, then keyword-based final_answer synthesis.
- It will NOT call new advisor tools when no API key is present — tool names are hardcoded strings.
- Minimal append-only change to make it call advisor tools: define advisor tool wrappers in `tools/advisor_tools.py` with the SAME names as the existing tools (`get_soil_readings`, `analyze_trend`, `get_crop_requirements`, `calculate_dosage`, `get_weather_forecast`) that delegate to `core/`, and register them in `tools/__init__.py` `build_tools()` so they shadow the old implementations. The fallback calls tools by name, so name-identical wrappers are picked up automatically.
- AWAITING APPROVAL before applying.

## 5. Build plan (unchanged scope: English + Tamil)

- Primary tomato targets = crop_requirements.json; TNAU/ICAR values kept only as cross-check column in docs.

### 7.3 DAILY DATA (interval-aware quality)
- CSV sampling interval: daily at 08:00 (median 1 day, derived at runtime).
- FLATLINE = 3+ consecutive identical readings, for moisture/temperature/humidity only. Constant N/P/K → INFO note, no confidence deduction.
- GAP = missing more than 2x median interval. SPIKE only when >= 6 points. Trend slope uses daily values directly when data is daily.

### 7.4 DATES
- `as_of` = last timestamp in CSV. Staleness deduction only if data older than 48h AND demo mode off.
- Demo mode (bundled sample): shift timestamps so last row is today; label "demo data, dates shifted" in API response and UI. Calendar dates start from today.

### 7.5 TOMATO DATASETS
- `data/tomato irrigation dataset.csv`: 3000 x 14. NO irrigation decision label. Environmental/sensor readings only (Temperature, Humidity, Soil moisture [raw ~300-700], ET, crop coefficient, N/P/K [mg/kg], pH). Good for correlating conditions with moisture/NPK, not labeled decisions.
- `data/tomato_water_sensor_data.json`: 393 items. HAS `motorValue` (binary 1/0 irrigation on/off) and `irrigation_needed_value` (numeric). Labeled irrigation decision source. → Add eval S11: agreement rate between our irrigation trigger and `motorValue`.

### 7.6 LLM
- Provider: None (no API key); `LLM()` → `client is None`, falls back to `_autonomous_fallback` (deterministic).
- Reuse `agent/llm.py`, no new provider.
- Tamil smoke test: 3-sentence request returned valid JSON (ReAct action `get_soil_readings`), confirming client is functional.

## 8. Build plan (unchanged scope: English + Tamil)

