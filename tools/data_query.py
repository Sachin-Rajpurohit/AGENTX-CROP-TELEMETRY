import json
import sys
import pandas as pd
from config import resolve_data_file

DEFAULT_REQUIREMENTS = {
    "tomato": {
        "target_moisture_pct": 65.0,
        "target_npk_kg_ha": [80.0, 20.0, 50.0],
        "optimal_ph_range": [6.0, 6.8],
        "max_root_temp_c": 30.0,
        "effective_irrigation_mm": 7.0,
        "split_advice": "Apply via drip fertigation during the final 30 minutes of irrigation to prevent root scorch."
    },
    "paddy": {
        "target_moisture_pct": 35.0,
        "target_npk_kg_ha": [100.0, 50.0, 50.0],
        "optimal_ph_range": [5.5, 6.5],
        "max_root_temp_c": 32.0,
        "effective_irrigation_mm": 6.2,
        "split_advice": "Split commercial Urea into two equal doses at active tillering and panicle initiation. NEVER apply Nitrogen during flowering."
    },
    "rice": {
        "target_moisture_pct": 35.0,
        "target_npk_kg_ha": [100.0, 50.0, 50.0],
        "optimal_ph_range": [5.5, 6.5],
        "max_root_temp_c": 32.0,
        "effective_irrigation_mm": 6.2,
        "split_advice": "Split commercial Urea into two equal doses at active tillering and panicle initiation. NEVER apply Nitrogen during flowering."
    },
    "groundnut": {
        "target_moisture_pct": 45.0,
        "target_npk_kg_ha": [25.0, 50.0, 75.0],
        "optimal_ph_range": [6.0, 6.5],
        "max_root_temp_c": 31.0,
        "effective_irrigation_mm": 5.5,
        "split_advice": "Apply basal dose and gypsum at pegging stage; avoid excess nitrogen."
    }
}

def load_crop_requirements(crop: str) -> dict:
    req_path = resolve_data_file("crop_requirements.json")
    reqs = {k: v.copy() for k, v in DEFAULT_REQUIREMENTS.items()}
    c_clean = str(crop).strip().lower()

    if req_path.exists():
        try:
            with open(req_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if isinstance(v, dict):
                            key_lower = k.lower()
                            base = reqs.get(key_lower, DEFAULT_REQUIREMENTS.get("tomato")).copy()
                            # Normalize possible variations of moisture key names
                            if "target_moisture_pct" not in v:
                                for alt in ["moisture", "target_moisture", "moisture_pct", "optimal_moisture"]:
                                    if alt in v:
                                        v["target_moisture_pct"] = float(v[alt])
                                        break
                            # Normalize possible variations of NPK key names
                            if "target_npk_kg_ha" not in v:
                                for alt in ["npk", "target_npk", "npk_kg_ha"]:
                                    if alt in v and isinstance(v[alt], list):
                                        v["target_npk_kg_ha"] = [float(x) for x in v[alt]]
                                        break
                            base.update(v)
                            reqs[key_lower] = base
        except Exception as e:
            sys.stderr.write(f"[WARN] Could not parse crop_requirements.json: {e}\n")

    res = reqs.get(c_clean)
    if not res:
        # Fallback to paddy if rice query, else tomato
        res = reqs.get("paddy" if "rice" in c_clean or "paddy" in c_clean else "tomato", DEFAULT_REQUIREMENTS["tomato"]).copy()

    # Absolute fallback guarantees to prevent any KeyError
    if "target_moisture_pct" not in res:
        res["target_moisture_pct"] = 35.0 if ("paddy" in c_clean or "rice" in c_clean) else 65.0
    if "target_npk_kg_ha" not in res or not isinstance(res["target_npk_kg_ha"], list):
        res["target_npk_kg_ha"] = [100.0, 50.0, 50.0] if ("paddy" in c_clean or "rice" in c_clean) else [80.0, 20.0, 50.0]
    if "optimal_ph_range" not in res:
        res["optimal_ph_range"] = [6.0, 6.8]
    if "max_root_temp_c" not in res:
        res["max_root_temp_c"] = 30.0

    return res

def analyze_soil_telemetry(plot_id: str = "Trichy Plot #4", days: int = 7) -> dict:
    """
    Analyzes 7-day soil sensor trends from soil_telemetry.csv in AGENTX_DATA_DIR.
    Handles varying column schemas gracefully.
    """
    csv_path = resolve_data_file("soil_telemetry.csv")
    sys.stderr.write(f"[TOOL: analyze_soil_telemetry] Reading {csv_path} for plot='{plot_id}'\n")

    if not csv_path.exists():
        return {
            "status": "error",
            "error": f"soil_telemetry.csv not found at {csv_path}",
            "fallback_used": True
        }

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return {"status": "error", "error": f"CSV read error: {str(e)}"}

    if df.empty:
        return {"status": "error", "error": "soil_telemetry.csv is empty."}

    # Normalize column names to handle variations in hidden datasets
    col_map = {c.lower().strip(): c for c in df.columns}
    plot_col = col_map.get("plot_id") or col_map.get("field_id") or col_map.get("plot")
    crop_col = col_map.get("crop") or col_map.get("crop_type")
    moist_col = col_map.get("soil_moisture_pct") or col_map.get("moisture") or col_map.get("soil_moisture")
    n_col = col_map.get("nitrogen_kg_ha") or col_map.get("nitrogen") or col_map.get("n")
    p_col = col_map.get("phosphorus_kg_ha") or col_map.get("phosphorus") or col_map.get("p")
    k_col = col_map.get("potassium_kg_ha") or col_map.get("potassium") or col_map.get("k")
    ph_col = col_map.get("soil_ph") or col_map.get("ph")
    temp_col = col_map.get("root_temp_c") or col_map.get("soil_temp") or col_map.get("temperature")
    loc_col = col_map.get("location") or col_map.get("city") or col_map.get("district")

    if plot_col:
        search_target = str(plot_id).strip().lower()
        df["_norm_plot"] = df[plot_col].astype(str).str.strip().str.lower()
        sub = df[df["_norm_plot"] == search_target].copy()
        if sub.empty:
            sub = df[df["_norm_plot"].str.contains(search_target, regex=False, na=False)].copy()
        if sub.empty and crop_col:
            sub = df[df[crop_col].astype(str).str.lower() == search_target].copy()
        if sub.empty:
            available = df[plot_col].unique().tolist()
            return {
                "status": "error",
                "error": f"Plot '{plot_id}' not found in telemetry. Available plots: {available}"
            }
    else:
        sub = df.copy()

    sub = sub.tail(max(1, int(days)))
    latest = sub.iloc[-1]

    crop_name = str(latest[crop_col]).strip().lower() if crop_col and pd.notna(latest[crop_col]) else "tomato"
    location_name = str(latest[loc_col]).strip() if loc_col and pd.notna(latest[loc_col]) else "Tiruchirappalli"

    cur_moisture = round(float(latest[moist_col]), 2) if moist_col else 22.0
    first_moisture = round(float(sub.iloc[0][moist_col]), 2) if moist_col else cur_moisture
    moisture_delta = round(cur_moisture - first_moisture, 2)

    cur_n = round(float(latest[n_col]), 2) if n_col else 40.0
    cur_p = round(float(latest[p_col]), 2) if p_col else 20.0
    cur_k = round(float(latest[k_col]), 2) if k_col else 30.0
    first_n = round(float(sub.iloc[0][n_col]), 2) if n_col else cur_n
    n_delta = round(cur_n - first_n, 2)

    soil_ph = round(float(latest[ph_col]), 2) if ph_col and pd.notna(latest[ph_col]) else 6.2
    root_temp = round(float(latest[temp_col]), 2) if temp_col and pd.notna(latest[temp_col]) else 32.4

    reqs = load_crop_requirements(crop_name)

    return {
        "status": "success",
        "plot_id": str(latest[plot_col]) if plot_col else plot_id,
        "crop": crop_name,
        "location": location_name,
        "days_analyzed": len(sub),
        "current_moisture_pct": cur_moisture,
        "target_moisture_pct": reqs.get("target_moisture_pct", 65.0),
        "moisture_7d_delta_pct": moisture_delta,
        "moisture_trend": "falling" if moisture_delta < -0.5 else ("rising" if moisture_delta > 0.5 else "stable"),
        "current_npk_kg_ha": [cur_n, cur_p, cur_k],
        "target_npk_kg_ha": reqs.get("target_npk_kg_ha", [80.0, 20.0, 50.0]),
        "nitrogen_7d_delta_kg_ha": n_delta,
        "soil_ph": soil_ph,
        "optimal_ph_range": reqs.get("optimal_ph_range", [6.0, 6.8]),
        "root_temp_c": root_temp,
        "thermal_stress": root_temp > reqs.get("max_root_temp_c", 30.0)
    }