import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.llm import generate_llm_synthesis, GROQ_MODELS
from agent.prompt_builder import build_synthesis_prompt, SYSTEM_PROMPT

def test_prompt_builder():
    """Verify synthesis prompt generation includes all grounding data."""
    query = "Evaluate Trichy Plot #4 (Tomato)"
    trace = [{"thought": "Step 1", "tool": "analyze_soil_telemetry", "args": {}, "observation": "{}"}]
    soil_obs = {"current_moisture_pct": 22.0, "current_npk_kg_ha": [40, 20, 30]}
    weather_obs = {"max_rain_probability_pct": 15, "total_rainfall_mm": 0.4}
    dosage_obs = {"commercial_fertilizer_kg_per_acre": {"urea_46_pct_N_kg": 35.2}}

    prompt = build_synthesis_prompt(query, trace, soil_obs, weather_obs, dosage_obs)
    assert "User Query: Evaluate Trichy Plot #4" in prompt
    assert "22.0" in prompt
    assert "35.2" in prompt
    assert "Verified Tool Observations" in prompt
    print("  [PASS] test_prompt_builder")

def test_llm_active_models_configured():
    """Verify that active Groq models are configured."""
    assert len(GROQ_MODELS) >= 2
    assert any("gpt-oss" in m or "qwen" in m for m in GROQ_MODELS)
    print("  [PASS] test_llm_active_models_configured")

def test_llm_graceful_recovery():
    """Verify that generate_llm_synthesis never raises an unhandled exception."""
    test_prompt = "Say test in one word."
    try:
        res = generate_llm_synthesis(test_prompt)
        assert isinstance(res, str)
        print("  [PASS] test_llm_graceful_recovery (Returned without throwing)")
    except Exception as e:
        assert False, f"generate_llm_synthesis must never throw unhandled error, got: {e}"

def run_all():
    print("Running Suite: tests/test_llm.py...")
    test_prompt_builder()
    test_llm_active_models_configured()
    test_llm_graceful_recovery()
    print("All LLM tests passed successfully!\n")

if __name__ == "__main__":
    run_all()
