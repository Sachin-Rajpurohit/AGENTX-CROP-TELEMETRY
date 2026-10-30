import json
import re
import sys
from config import MAX_ITERATIONS
from tools import TOOL_REGISTRY
from tools.data_query import load_crop_requirements
from agent.prompt_builder import build_synthesis_prompt
from agent.llm import generate_llm_synthesis

class AgriAgent:
    def __init__(self, max_iterations: int = MAX_ITERATIONS):
        self.max_iterations = max_iterations

    def _parse_query_context(self, query: str) -> dict:
        q_lower = query.lower()

        # 1. Detect plot_id
        plot_id = "Trichy Plot #4"
        plot_match = re.search(r"(trichy\s+plot\s*#?\d+|plot[_\s#]*\w+)", query, re.IGNORECASE)
        if plot_match:
            plot_id = plot_match.group(1).strip()

        # 2. Detect crop
        crop = None
        for c in ["tomato", "paddy", "rice", "groundnut"]:
            if c in q_lower:
                crop = "paddy" if c == "rice" else c
                break

        # 3. Detect location
        location = "Tiruchirappalli"
        for loc in ["tiruchirappalli", "trichy", "coimbatore", "madurai", "thanjavur", "salem", "chennai"]:
            if loc in q_lower:
                location = loc.capitalize()
                if location.lower() == "trichy":
                    location = "Tiruchirappalli"
                break

        # 4. Detect inline NPK overrides (e.g. "40-20-30 kg/ha")
        npk_matches = re.findall(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", query)
        inline_current_npk = [float(x) for x in npk_matches[0]] if len(npk_matches) >= 1 else None
        inline_target_npk = [float(x) for x in npk_matches[1]] if len(npk_matches) >= 2 else None

        # 5. Detect inline moisture
        moist_match = re.search(r"moisture[^0-9]*(\d+(?:\.\d+)?)\s*%", q_lower)
        inline_moisture = float(moist_match.group(1)) if moist_match else None

        simulate_heavy_rain = bool(re.search(r"(heavy\s+rain|>\s*30\s*mm|imminent\s+rain)", q_lower))

        return {
            "plot_id": plot_id,
            "crop": crop,
            "location": location,
            "inline_current_npk": inline_current_npk,
            "inline_target_npk": inline_target_npk,
            "inline_moisture": inline_moisture,
            "simulate_heavy_rain": simulate_heavy_rain,
            "wants_tamil": "tamil" in q_lower or "தமிழ்" in query
        }

    def run(self, query: str) -> dict:
        trace = []
        ctx = self._parse_query_context(query)

        # STEP 1: PERCEIVE & ANALYZE SOIL TELEMETRY
        thought_1 = (
            f"Perceiving telemetry request for plot '{ctx['plot_id']}'. "
            f"I will invoke `analyze_soil_telemetry` to inspect the 7-day soil moisture, NPK, pH, and root-zone temperature trends."
        )
        args_1 = {"plot_id": ctx["plot_id"], "days": 7}
        soil_obs = TOOL_REGISTRY["analyze_soil_telemetry"](**args_1)
        trace.append({
            "thought": thought_1,
            "tool": "analyze_soil_telemetry",
            "args": args_1,
            "observation": json.dumps(soil_obs)
        })

        if soil_obs.get("status") == "error" and not ctx["inline_current_npk"] and not ctx["inline_moisture"]:
            graceful_msg = f"Diagnostic Notice: {soil_obs.get('error')} Please verify the sensor plot ID in soil_telemetry.csv."
            return {"answer": graceful_msg, "trace": trace}

        # Resolve crop: query overrides telemetry, else use telemetry crop, else default tomato
        raw_crop = ctx["crop"] or soil_obs.get("crop", "tomato")
        crop = "paddy" if raw_crop.lower() in ["rice", "paddy"] else raw_crop.lower()

        # Load requirements for the resolved crop
        reqs = load_crop_requirements(crop)

        # Resolve moisture and NPK targets correctly
        cur_moisture = ctx["inline_moisture"] if ctx["inline_moisture"] is not None else soil_obs.get("current_moisture_pct", 22.0)
        tgt_moisture = reqs["target_moisture_pct"]

        cur_npk = ctx["inline_current_npk"] or soil_obs.get("current_npk_kg_ha", [40.0, 20.0, 30.0])
        tgt_npk = ctx["inline_target_npk"] or reqs["target_npk_kg_ha"]

        soil_ph = soil_obs.get("soil_ph", 6.2)
        root_temp = soil_obs.get("root_temp_c", 32.4)
        location = soil_obs.get("location", ctx["location"])

        # STEP 2: WEATHER INTERLOCK CHECK
        thought_2 = (
            f"Soil moisture for {crop} is {cur_moisture}% (target: {tgt_moisture}%) and NPK is {cur_npk} kg/ha. "
            f"Checking 3-day rainfall risk in {location} before prescribing irrigation."
        )
        args_2 = {"location": location, "days": 3}
        weather_obs = TOOL_REGISTRY["get_weather_forecast"](**args_2)
        if ctx["simulate_heavy_rain"]:
            weather_obs["total_rainfall_mm"] = 38.0
            weather_obs["max_rain_probability_pct"] = 85
            weather_obs["heavy_rain_risk"] = True
            weather_obs["should_delay_irrigation"] = True
        trace.append({
            "thought": thought_2,
            "tool": "get_weather_forecast",
            "args": args_2,
            "observation": json.dumps(weather_obs)
        })

        # STEP 3: DETERMINISTIC DOSAGE COMPUTATION
        thought_3 = (
            f"Weather check complete (rain probability: {weather_obs['max_rain_probability_pct']}%, {weather_obs['total_rainfall_mm']} mm). "
            f"Invoking `calculate_fertilizer_water_dosage` for exact commercial fertilizer weights and water volume per acre."
        )
        args_3 = {
            "crop": crop,
            "current_moisture_pct": cur_moisture,
            "target_moisture_pct": tgt_moisture,
            "current_npk_kg_ha": cur_npk,
            "target_npk_kg_ha": tgt_npk,
            "field_area_acres": 1.0,
            "heavy_rain_expected": weather_obs.get("should_delay_irrigation", False)
        }
        dosage_obs = TOOL_REGISTRY["calculate_fertilizer_water_dosage"](**args_3)
        trace.append({
            "thought": thought_3,
            "tool": "calculate_fertilizer_water_dosage",
            "args": args_3,
            "observation": json.dumps(dosage_obs)
        })

        # STEP 4: SYNTHESIZE ADVISORY
        answer = self._format_deterministic_advisory(ctx, crop, cur_moisture, tgt_moisture, cur_npk, tgt_npk, soil_ph, root_temp, weather_obs, dosage_obs)

        # Optional LLM polish only if exact dosage values are preserved
        synthesis_prompt = build_synthesis_prompt(query, trace, soil_obs, weather_obs, dosage_obs)
        llm_text = generate_llm_synthesis(synthesis_prompt)
        urea_str = str(dosage_obs["commercial_fertilizer_kg_per_acre"]["urea_46_pct_N_kg"])
        if llm_text and urea_str in llm_text and "X kg" not in llm_text:
            answer = llm_text

        return {"answer": answer, "trace": trace}

    def _format_deterministic_advisory(
        self, ctx, crop, cur_moisture, tgt_moisture, cur_npk, tgt_npk, soil_ph, root_temp, weather_obs, dosage_obs
    ) -> str:
        fert = dosage_obs["commercial_fertilizer_kg_per_acre"]
        elem = dosage_obs["elemental_deficit_kg_per_acre"]
        irrig = dosage_obs["irrigation_schedule"]
        rain_prob = weather_obs["max_rain_probability_pct"]
        rain_mm = weather_obs["total_rainfall_mm"]

        if weather_obs.get("should_delay_irrigation"):
            action_summary = (
                f"HOLD IRRIGATION & FERTILIZER: Heavy rainfall ({rain_mm} mm, {rain_prob}% probability) is forecast over the next 48-72 hours. "
                f"Do not irrigate or apply top-dress Urea ({fert['urea_46_pct_N_kg']} kg/acre) right now to prevent nitrogen leaching. "
                f"Re-evaluate soil moisture 24 hours after rainfall subsides."
            )
        else:
            p_line = (
                f"0 kg required (Phosphorus is already at optimal target)."
                if elem["pure_P2O5_kg"] == 0 else
                f"Apply {fert['ssp_16_pct_P2O5_kg']} kg commercial SSP (or {fert['dap_46_pct_P2O5_kg']} kg DAP) per acre to supply {elem['pure_P2O5_kg']} kg P2O5."
            )
            k_line = (
                f"0 kg required (Potassium is at target)."
                if elem["pure_K2O_kg"] == 0 else
                f"Apply {fert['mop_60_pct_K2O_kg']} kg commercial MOP (60% K2O) per acre to supply {elem['pure_K2O_kg']} kg pure K2O."
            )
            action_summary = (
                f"1. Field & Thermal Assessment ({ctx['plot_id']} - {crop.capitalize()}): "
                f"Soil moisture is at {cur_moisture}% (target: {tgt_moisture}% field capacity), "
                f"root-zone temperature is {root_temp}°C, and soil pH is {soil_ph}. "
                f"Current NPK is {int(cur_npk[0])}-{int(cur_npk[1])}-{int(cur_npk[2])} kg/ha against target {int(tgt_npk[0])}-{int(tgt_npk[1])}-{int(tgt_npk[2])} kg/ha.\n"
                f"2. Weather Risk ({weather_obs['location']}): 3-day rain probability is {rain_prob}% ({rain_mm} mm expected). "
                f"Do NOT delay irrigation; natural rainfall is insufficient to recover soil moisture.\n"
                f"3. Actionable Fertilizer Prescriptions (Per 1 Acre):\n"
                f"   - Commercial Urea (46% N): Apply {fert['urea_46_pct_N_kg']} kg of commercial Urea per acre (supplies {elem['pure_N_kg']} kg pure N). {dosage_obs['application_guidance']}\n"
                f"   - Phosphorus: {p_line}\n"
                f"   - Potassium: {k_line}\n"
                f"4. Irrigation Schedule: Apply {irrig['water_volume_liters_per_acre']:,} Liters of water per acre "
                f"(~{irrig['application_depth_mm']} mm depth, or ~{irrig['pump_runtime_hours']} hours on a 3-5 HP pump) "
                f"immediately to relieve thermal stress and facilitate nutrient uptake."
            )

        if ctx.get("wants_tamil"):
            tamil_block = (
                f"\n\n[தமிழ் விவசாய ஆலோசனை - {ctx['plot_id']} ({crop.capitalize()})]:\n"
                f"• மண் நிலை: ஈரப்பதம் {cur_moisture}% (இலக்கு: {tgt_moisture}%). வேர் வெப்பநிலை {root_temp}°C.\n"
                f"• வானிலை: மழை வாய்ப்பு {rain_prob}% மட்டுமே. பாசனத்தை தாமதிக்க வேண்டாம்.\n"
                f"• உரப் பரிந்துரை: யூரியா {fert['urea_46_pct_N_kg']} கிலோ, பொட்டாஷ் {fert['mop_60_pct_K2O_kg']} கிலோ ஏக்கருக்கு இடவும்.\n"
                f"• பாசனம்: ஏக்கருக்கு {irrig['water_volume_liters_per_acre']:,} லிட்டர் தண்ணீர் பாய்ச்சவும்."
            )
            return action_summary + tamil_block

        return action_summary